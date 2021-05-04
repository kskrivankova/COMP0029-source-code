from cuttlefish.sec import Measure
from cuttlefish.packet_management import attr
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from functools import reduce

import os


class AESEncryptSim(Measure):
    def __init__(self, target, enc_key, dec_key, *args, **kwargs):
        super().__init__(target, *args, **kwargs)

        # Account for addition of initialization vector
        self.target = target
        self.enc_key = enc_key
        self.dec_key = dec_key

        self.iv_layer = max(target)

        self.encoding_scheme = None
        self.decoding_scheme = None

        self.iv_scheme = attr("iv", 16)

    def apply(self, serializer):
        self.encoding_scheme = serializer.encoding_scheme.scheme
        self.decoding_scheme = serializer.decoding_scheme.scheme

        serializer.add_attr(self.iv_scheme, self.iv_layer)

    def process_send(self, data):
        data[self.iv_layer].append(bytes(16))
        return data

    def encode(self, data):
        iv = os.urandom(16)
        data[self.iv_layer][-1] = iv

        cipher = Cipher(algorithms.AES(self.enc_key), modes.CTR(iv))
        encryptor = cipher.encryptor()

        plaintext = reduce(lambda x, y: x + y, self.enc_attr_generator(data))

        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        self.update_enc_data(data, ciphertext)

        return data

    def decode(self, data):
        iv = data[self.iv_layer]["iv"]

        cipher = Cipher(algorithms.AES(self.dec_key), modes.CTR(iv))
        decryptor = cipher.decryptor()

        ciphertext = reduce(lambda x, y: x + y, self.dec_attr_generator(data))

        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        self.update_dec_data(data, plaintext)

        return data

    def process_recv(self, data):
        data[self.iv_layer].pop("iv")
        return data

    def add_padding_size(self):
        scheme = self.encoding_scheme
        size_sum = 0

        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                size_sum += scheme[layer_i][attr_i].get("size")

        padding_size = (-size_sum) % 16

        attr_layer = max(self.target)
        attr_index = max(self.target[attr_layer])
        attr_size_update = padding_size + self.encoding_scheme[attr_layer][attr_index].get("size")

        self.update_attr_data(attr_size_update, attr_layer, attr_index)

    def update_attr_data(self, data, layer, index):
        encoding_scheme = self.encoding_scheme
        decoding_scheme = self.decoding_scheme

        encoding_scheme[layer][index].update({"size": data})
        decoding_scheme[layer][index].update({"size": data})

    def enc_attr_generator(self, data):
        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                yield data[layer_i][attr_i]

    def dec_attr_generator(self, data):
        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                attr_name = self.encoding_scheme[layer_i][attr_i].get("name")
                yield data[layer_i][attr_name]

    def update_enc_data(self, data, ciphertext, encoding=True):
        scheme = self.encoding_scheme if encoding else self.decoding_scheme
        slice_start = 0

        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                attr_size = scheme[layer_i][attr_i].get("size")
                slice_end = slice_start + attr_size

                data[layer_i][attr_i] = ciphertext[slice_start:slice_end]
                slice_start = slice_end

    def update_dec_data(self, data, ciphertext, encoding=True):
        scheme = self.encoding_scheme if encoding else self.decoding_scheme
        slice_start = 0

        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                attr_size = scheme[layer_i][attr_i].get("size")
                attr_name = scheme[layer_i][attr_i].get("name")
                slice_end = slice_start + attr_size

                data[layer_i].update({attr_name: ciphertext[slice_start:slice_end]})
                slice_start = slice_end
