from cuttlefish.packet_management import attr, BYTES
from cuttlefish.channel.measure import *
from hashlib import sha256
from hmac import new


class HMAC(Measure):
    """
    target = {
        [layer_index:  attr_names,*    ]*
    }
    """
    def __init__(self, target, enc_key, dec_key, *args, **kwargs):
        super().__init__(target, *args, **kwargs)

        self.target = target

        self.enc_key = enc_key
        self.dec_key = dec_key
        self.digest_mode = sha256
        # TODO: configure mac size according to digest mode
        self.mac_size = 32

        self.hmac_attr_scheme = attr("hmac", self.mac_size)
        self.encoding_scheme = None

    def apply(self, foundry):
        foundry.add_layer(headers=[self.hmac_attr_scheme])
        self.encoding_scheme = foundry.encoding_scheme.scheme

    def process_send(self, data, meta, *args):
        hmac_layer = [bytes(self.mac_size)]
        data.append(hmac_layer)
        return data

    def encode(self, data):
        hmac = new(self.enc_key, digestmod=sha256)

        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                hmac.update(data[layer_i][attr_i])

        digest = hmac.digest()
        data[-1][0] = digest

        return data

    def decode(self, data):
        hmac = new(self.dec_key, digestmod=sha256)

        for layer_i, attributes in self.target.items():
            for attr_i in attributes:
                attr_name = self.encoding_scheme[layer_i][attr_i].get("name")
                hmac.update(data[layer_i][attr_name])

        data_digest = hmac.digest()
        packet_digest = data[-1]["hmac"]

        if data_digest == packet_digest:
            return data

        return None

    def process_recv(self, data):
        data.pop()
        return data
