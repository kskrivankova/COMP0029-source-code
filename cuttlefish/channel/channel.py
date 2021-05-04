from cuttlefish.packet_management import Serializer
from cuttlefish.sec import Security


class Channel:
    def __init__(
        self,
        id_generator,
        orchestrator,
        scheduler,
        encoding_scheme,
        network,
        decoding_scheme=None,
        security_scheme=None,
        encode_callbacks=None,
        decode_callbacks=None,
    ):
        self.channel_id = next(id_generator)
        self.processed_callback = None

        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self.serializer = Serializer(
            encoding_scheme,
            decoding_scheme=decoding_scheme,
            encode_callbacks=encode_callbacks,
            decode_callbacks=decode_callbacks,
        )
        self.network = network
        self.sec = Security(self.serializer, security_scheme)

        self.sec.append_channel(network)

    def init_connection(self, socket, *args, mode=None, meta=None, buffer_size=10, recv_callback=None,
                        sent_callback=None, processed_callback=None, **kwargs):

        self.network.init_connection(
            socket,
            self.channel_id,
            self.serializer,
            self.orchestrator,
            self.scheduler,
            *args,
            channel=self,
            mode=mode,
            meta=meta,
            buffer_size=buffer_size,
            recv_callback=recv_callback,
            sent_callback=sent_callback,
            **kwargs
        )

        self.sec.init_measures()
        self.orchestrator.processed_callback[self.channel_id] = processed_callback

    def get_id(self):
        return self.channel_id

    def send(self, data, *args, ack_type=0, **kwargs):
        meta = {}

        self.network.process_send(data, meta, *args, ack_type=ack_type, **kwargs)

        if self.sec:
            self.sec.process_send(data, meta, *args)

        serialized_data = self.serialize(data)

        self.network.send(serialized_data, meta)

        return meta

    def serialize(self, data):
        return self.serializer.encode(data)

    def deserialize(self, data, meta):
        return self.serializer.decode(data, meta)

    def process(self, data, meta, *args, **kwargs):
        decoded_data = self.deserialize(data, meta)

        decoded_data = self.sec.process_recv(decoded_data, meta)

        if not decoded_data:
            return None

        decoded_data = self.network.process_recv(decoded_data, meta, args, kwargs)

        return decoded_data

    def receive(self):
        return self.network.receive()

    def disconnect(self):
        self.network.disconnect()
