try:
    from uhashlib import hash
    from crypto import AES
    import crypto
except Exception:
    from hashlib import sha256
    import hmac

    pass


class Security:
    """
    Defines security features. Input is a list of security measures (callback) and where to apply it
    (layers(x:y)attributes(a:b))
    """

    HMAC = "hmac"

    def __init__(self, foundry, measures):
        self.foundry = foundry
        self.channel = None
        self.measures = measures if measures else []

        self.encode_pipeline = foundry.encode_callbacks
        self.decode_pipeline = foundry.decode_callbacks

        self.send_pipeline = []
        self.recv_pipeline = []

    def append_channel(self, channel):
        self.channel = channel

        return channel

    def init_measures(self):
        for measure in self.measures:
            measure.apply(self.foundry)

            self.encode_pipeline.append(measure.encode)
            self.decode_pipeline.append(measure.decode)
            self.decode_pipeline.reverse()

            self.send_pipeline.append(measure.process_send)
            self.recv_pipeline.append(measure.process_recv)
            self.recv_pipeline.reverse()

    def process_send(self, data, meta, *args):
        for callback in self.send_pipeline:
            data = callback(data, meta, *args)

            if not data:
                break

        return

    def process_recv(self, data, meta):
        for callback in self.recv_pipeline:
            data = callback(data, meta)

            if not data:
                break

        return data
