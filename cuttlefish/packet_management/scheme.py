from .errors import *


class Scheme:
    """
    AttributeScheme class defines the packet structure and properties of individual attributes.
    Scheme is a tuple of in-order attribute definitions, ie. order of attributes in a packet is the same as
    order of attributes defined in the scheme.

    Attribute definition is a dictionary defined as follows:

        {
            'name': str,
            'size': int,
            'type': str,
            'parsing_callback': callback,
            'encoding_callback': callback,
            'decoding_callback': callback,
        }

    Name and size are always mandatory, while type always defaults to bytes. If 'size' is defined to be 0,
    it is considered that attribute size is variable. If size of an attribute is variable, it necessitates
    definition of a callback that returns an integer that is the size of the attribute.
    For this purpose, it is possible to define dependencies.
    Type, if not defined, is considered to be bytes. Allowed types are:

        Type      |  Representation
        ===========================
        bytes     |      'b'
        integer   |      'i'
        string    |      's'
        custom    |      '*'

    Custom type requires that both encoding and decoding callbacks are defined. If either callback is defined for an
    attribute of any type, it will be used for encoding or decoding by default. encoding_callback() accepts a parameter
    with attribute data to be encoded and returns the data encoded in bytes. decoding_callback() accepts a parameter
    containing byte data and returns the data decoded back into its determined type.
    TODO: add docs for callbacks

    To further address the possibility of attributes of variable size, it is possible to define attribute
    dependencies. Each dependency is an entry in a dictionary, where the key represents the name of
    dependent attribute. It's value par is a dictionary with `layer position: tuple(attribute name+)` pairs. This implies
    that all attribute names should be distinct.



        {
            (1, 2): (0: ("frame",))
            (1, 5): (0: ("size", "count")),
        }

    For nested schemes, dependencies can be only defined for attributes within the same level.

    """

    attribute_types = ("b", "i", "s", "*")

    def __init__(self, encoding_scheme, dependencies=None):
        self.scheme = encoding_scheme
        self.dependencies = dependencies

    def __repr__(self):
        layer_repr = []

        for layer in self.scheme:
            layer_repr_item = "\t[\n" + "".join(("\t\t" + str(attribute) + ",\n") for attribute in layer)
            layer_repr_item += "\t],\n"

            layer_repr.append(layer_repr_item)
            
        scheme = "Dependencies: {}\n".format(self.dependencies)
        scheme += "Scheme:" + "".join(layer_repr)

        return scheme


BYTES = "b"
INT = "i"
STR = "s"
NDEC = "n"
CUSTOM = "*"


# TODO: update docs
def attr(
    name,
    size,
    type=None,
    parsing_callback=None,
    encode_type_callback=None,
    decode_type_callback=None,
    **kwargs
):
    if size < 0:
        raise AttributeSizeNotAllowed
    if (size == 0) and not parsing_callback:
        raise CallbackNotDefined

# TODO: kwargs?
    return dict([
        ("name", name),
        ("size", size),
        ("type", type),
        ("parsing_callback", parsing_callback),
        ("encode_type_callback", encode_type_callback),
        ("decode_type_callback", decode_type_callback)
    ])


def delimiter():
    return "*"


def layer(*args):
    return list(args)


def get_scheme(*args):
    return list(args)
