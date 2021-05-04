from .errors import (
    UnexpectedInputSize,
    AttributeTypeNotRecognized,
)
from .scheme import BYTES, INT, STR
from .ordered_dict import OrderedDict


class Serializer:
    def __init__(
        self,
        encoding_scheme,
        decoding_scheme=None,
        encode_callbacks=None,
        decode_callbacks=None,
    ):
        self.encoding_scheme = encoding_scheme
        self.decoding_scheme = (
            encoding_scheme if not decoding_scheme else decoding_scheme
        )

        self.encode_callbacks = encode_callbacks if encode_callbacks else []
        self.decode_callbacks = decode_callbacks if decode_callbacks else []

    def encode(self, input_attributes):
        encoded_attributes = self.encode_type(input_attributes)

        if self.encode_callbacks:
            for encode_callback in self.encode_callbacks:
                encoded_attributes = encode_callback(encoded_attributes)

        encoded_attributes = self.encode_layers(encoded_attributes)

        return encoded_attributes

    def decode(self, input_bytes, meta):
        decoded_attributes = self.decode_layers(input_bytes)

        redundant_bytes = decoded_attributes[1]
        decoded_attributes = decoded_attributes[0]

        if self.decode_callbacks:
            for decode_callback in self.decode_callbacks:
                decode_callback(decoded_attributes)

        decoded_attributes = self.decode_type(decoded_attributes)

        meta.update({"redundant_bytes": redundant_bytes})

        return decoded_attributes

    def encode_layers(self, attributes):
        encoding_scheme = self.encoding_scheme.scheme
        byte_data = b""
        scheme_len = len(encoding_scheme) - 1

        # Encode headers
        for i, layer_scheme in enumerate(reversed(encoding_scheme)):
            for attr_scheme, attribute in header_scheme_generator(layer_scheme, attributes[scheme_len - i]):

                encoded_attribute = encode_attribute(
                    attr_scheme, attribute
                )

                byte_data += encoded_attribute

        # Encode trailers
        for i, layer_scheme in enumerate(encoding_scheme):
            for attr_scheme, attribute in trailer_scheme_generator(layer_scheme, attributes[i]):
                encoded_attribute = encode_attribute(attr_scheme, attribute)

                byte_data += encoded_attribute

        return byte_data

    # Decode attributes layer by layer
    def decode_layers(self, input_bytes):
        packet_scheme = self.decoding_scheme.scheme
        dependencies = self.decoding_scheme.dependencies

        scheme_len = len(packet_scheme)
        input_bytes = list(input_bytes)
        decoded_layers = []

        for i, layer_scheme in enumerate(reversed(packet_scheme)):

            decoded_layer = decode_layer(
                input_bytes, layer_scheme, dependencies, decoded_layers, scheme_len
            )
            decoded_layers.append(decoded_layer)

        decoded_layers.reverse()

        return decoded_layers, bytes(input_bytes)

    def encode_type(self, attributes):
        encoding_scheme = self.encoding_scheme.scheme
        encoded_attributes = []

        for i, layer_scheme in enumerate(encoding_scheme):
            encoded_layer = map(
                encode_attr_type, enc_attr_scheme_generator(layer_scheme), attributes[i]
            )
            encoded_attributes.append(list(encoded_layer))

        return encoded_attributes

    def decode_type(self, attributes):
        decoding_scheme = self.decoding_scheme.scheme

        for i, layer_scheme in enumerate(decoding_scheme):
            attr_layer = attributes[i]
            decoded_data = list(map(
                decode_attr_type, dec_attr_scheme_generator(layer_scheme), attr_layer.values()
            ))

            attr_layer.update(((key, decoded_data[v]) for v, key in enumerate(attr_layer)))

        return attributes

    def add_layer(self, headers=None, trailers=None, encoding=True, decoding=False):
        if (not headers) and (not trailers):
            raise TypeError(
                "Foundry: insufficient number of arguments when adding encoding layer"
            )

        new_layer = []

        if headers:
            new_layer.extend(headers)

        if trailers:
            new_layer.append("*")
            new_layer.extend(trailers)

        if encoding:
            encoding_scheme = self.encoding_scheme.scheme
            encoding_scheme.append(new_layer)
        if decoding and (self.encoding_scheme is not self.decoding_scheme):
            decoding_scheme = self.decoding_scheme.decoding_scheme
            decoding_scheme.append(new_layer)

    def add_attr(self, attr, layer, index=None, encoding=True, decoding=True):
        encoding_scheme = self.encoding_scheme.scheme
        decoding_scheme = self.decoding_scheme.scheme

        if encoding:
            index = index if index is not None else len(encoding_scheme[layer])
            encoding_scheme[layer].insert(index, attr)

        if decoding and (self.encoding_scheme is not self.decoding_scheme):
            index = index if index is not None else len(decoding_scheme[layer])
            decoding_scheme[layer].insert(index, attr)


def enc_attr_scheme_generator(layer_scheme):
    for attr_scheme in layer_scheme:
        if attr_scheme != "*":
            yield attr_scheme


def dec_attr_scheme_generator(layer_scheme):
    for attr_scheme in layer_scheme:
        if attr_scheme != "*":
            yield attr_scheme


def header_scheme_generator(layer_scheme, attribute_layer):
    for i, attr_scheme in enumerate(layer_scheme):
        if attr_scheme == "*":
            break

        yield attr_scheme, attribute_layer[i]


def trailer_scheme_generator(layer_scheme, attribute_layer):
    try:
        trailer_index = layer_scheme.index("*") + 1
    except ValueError:
        return

    for i in range(trailer_index, len(layer_scheme)):
        yield layer_scheme[i], attribute_layer[i - 1]


def encode_attribute(attribute_scheme, attribute):
    attr_size = attribute_scheme.get("size")

    if attr_size == 0:
        pass
    elif len(attribute) > attr_size:
        raise UnexpectedInputSize(
           "Size of data to be encoded ({}) exceeds defined size ({}).".format(len(attribute), attr_size),
        )

    elif len(attribute) < attr_size:
        raise UnexpectedInputSize(
            "Data to be encoded is smaller ({}) than expected ({}).".format(len(attribute), attr_size)
        )

    return attribute


def decode_layer(input_bytes, layer_scheme, dependencies, decoded_layers, scheme_len):
    decoded_attributes = OrderedDict()
    trailer_start = len(layer_scheme) - 1

# TODO: Fix this abomination
    # Decode headers
    for i, attribute_scheme in enumerate(layer_scheme):
        if attribute_scheme == "*":
            decoded_attributes.update({"*": None})
            trailer_start = i
            break

        attribute_size = attribute_scheme.get("size")

        if attribute_size == 0:
            attribute_name = attribute_scheme.get("name")
            attr_dependencies = dependencies.get(attribute_name)
            
            decoded_layers_temp = [decoded_attributes]
            decoded_layers_temp.extend(decoded_layers)

            attribute_size = resolve_dependencies(
                decoded_layers_temp, attribute_scheme, scheme_len, attr_dependencies
            )
            decoded_attribute = decode_attribute(
                input_bytes, attribute_scheme, attribute_size
            )
        else:
            decoded_attribute = decode_attribute(input_bytes, attribute_scheme)

        attribute_name = attribute_scheme.get("name")

        decoded_attributes.update({attribute_name: decoded_attribute})

    reverse_decoded_attributes = OrderedDict()
    input_bytes.reverse()

    # Decode trailers
    for i in range(len(layer_scheme) - 1, trailer_start, -1):
        attribute_scheme = layer_scheme[i]

        attribute_size = attribute_scheme.get("size")

        if attribute_size == 0:
            attribute_name = attribute_scheme.get("name")
            attr_dependencies = dependencies.get(attribute_name)
            decoded_layers_temp = [decoded_attributes]
            decoded_layers_temp.extend(decoded_layers)

            attribute_size = resolve_dependencies(
                decoded_layers_temp, attribute_scheme, scheme_len, attr_dependencies
            )
            decoded_attribute = decode_attribute(
                input_bytes, attribute_scheme, attribute_size
            )
        else:
            decoded_attribute = decode_attribute(input_bytes, attribute_scheme, attribute_size)

        decoded_attribute = decoded_attribute[::-1]
        decoded_attribute = decode_attr_type(attribute_scheme, decoded_attribute)

        decoded_attribute_name = attribute_scheme.get("name")

        reverse_decoded_attributes.update({decoded_attribute_name: decoded_attribute})

    input_bytes.reverse()
    decoded_attributes.update(
        [(k, v) for k, v in reversed(reverse_decoded_attributes.items())]
    )

    return decoded_attributes


def decode_attribute(input_bytes, attribute_scheme, attribute_size=None):
    decoded_attribute = b""

    if not attribute_size:
        attribute_size = attribute_scheme.get("size")

    try:
        for i in range(attribute_size):
            decoded_attribute += bytes([input_bytes.pop(0)])
    except IndexError:
        size = len(decoded_attribute)
        raise UnexpectedInputSize(
            "Size of input received ({}) was smaller than expected by scheme definition ({}).".format(size, attribute_size)
        )

    return decoded_attribute


def encode_attr_type(attribute_scheme, attribute_data):
    attribute_type = attribute_scheme.get("type")
    encoding_callback = attribute_scheme.get("encode_type_callback")

    if encoding_callback:
        encoded_data = encoding_callback(attribute_data)
    elif (attribute_type == BYTES) or not attribute_type:
        encoded_data = attribute_data
    elif attribute_type == INT:
        endianness = attribute_scheme.get("endianness")

        if endianness:
            encoded_data = encode_int(
                attribute_data, attribute_scheme.get("size"), endianness=endianness
            )
        else:
            encoded_data = encode_int(attribute_data, attribute_scheme.get("size"))

    elif attribute_type == STR:
        encoded_data = encode_string(attribute_data)
    else:
        raise AttributeTypeNotRecognized

    return encoded_data


def encode_int(data, size, endianness="big"):
    return data.to_bytes(size, endianness)


def encode_string(data):
    return data.encode()


def decode_attr_type(attribute_scheme, attribute_data):
    attribute_type = attribute_scheme.get("type")
    decoding_callback = attribute_scheme.get("decode_type_callback")

    if decoding_callback:
        decoded_data = decoding_callback(attribute_data)
    elif (attribute_type == BYTES) or not attribute_type:
        decoded_data = attribute_data
    elif attribute_type == INT:
        endianness = attribute_scheme.get("endianness")

        if endianness:
            decoded_data = decode_int(attribute_data, endianness=endianness)
        else:
            decoded_data = decode_int(attribute_data)

    elif attribute_type == STR:
        decoded_data = decode_string(attribute_data)
    else:
        raise AttributeTypeNotRecognized

    return decoded_data


def decode_int(attribute_data, endianness="big"):
    return int.from_bytes(attribute_data, endianness)


def decode_string(attribute_data):
    return attribute_data.decode()


def resolve_dependencies(
    decoded_attributes, attribute_scheme, scheme_len, dependencies=None
):

    try:
        requisite_attributes = fetch_requisite_attributes(
            decoded_attributes, dependencies, scheme_len
        )
    except KeyError:
        raise KeyError("Required attribute not found in parsed data.")
    except AttributeError:
        raise AttributeError("No dependency scheme was defined.")

    parsing_callback = attribute_scheme.get("parsing_callback")
    callback = parsing_callback if parsing_callback else default_callback

    return callback(*requisite_attributes)


def fetch_requisite_attributes(decoded_attributes, dependency, scheme_len):
    if not dependency:
        return []

    requisite_attributes = []

    for layer_i, attr_list in dependency.items():
        # Ensure correct indexing when all layers haven't been parsed
        reverse_i = layer_i - scheme_len

        for attr_name in attr_list:
            requisite_attribute = decoded_attributes[reverse_i][attr_name]
            requisite_attributes.append(requisite_attribute)

    return requisite_attributes


def default_callback(*args):
    return int.from_bytes(args[0], "big")
