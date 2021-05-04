from .network import Network, IS_ACK, NEEDS_ACK
from cuttlefish.packet_management import attr
from cuttlefish.ring_buffer import RingBuffer, RingBufferUnderflow


class Unicast(Network):
    def __init__(self, address, address_size=4, meta=None, buffer_size=10):
        super().__init__(address, address_size=address_size, meta=meta, buffer_size=buffer_size)

        self.dest_address = None

    def init_connection(
        self,
        socket,
        channel_id,
        serializer,
        orchestrator,
        scheduler,
        *args,
        ack=False,
        ack_callback=None,
        mode=None,
        schedule_callback=None,
        recv_buffer_size=32,
        **kwargs
    ):
        super().init_connection(
            socket,
            channel_id,
            serializer,
            orchestrator,
            scheduler,
            *args,
            ack=ack,
            ack_callback=ack_callback,
            recv_buffer_size=recv_buffer_size,
            mode=mode,
            schedule_callback=schedule_callback,
            **kwargs,
        )

        serializer.add_layer(headers=[self.address_scheme])

        self.ack_request_index = {} if ack else None

    def process_send(self, data, meta, *args, ack_type=0, **kwargs):
        dest_address = args[0]

        if ack_type & IS_ACK:
            buffer = self.ack_request_index.get(dest_address)

            try:
                self.next_ack_id = buffer.pop() if buffer else None
            except RingBufferUnderflow:
                ack_type = ack_type & 1
                pass

        super().process_send(data, meta, *args, ack_type=ack_type, **kwargs)

        self.dest_address = dest_address
        data.append([dest_address])

        return data

    def process_recv(self, data, meta, *args, **kwargs):
        address = data.pop()
        address = address["address"]

        if (address == self.address) or (address == self.promiscuous_address):
            data = super().process_recv(data, meta, *args, **kwargs)

            if not data:
                return None

            if meta.get("ack_type") and (meta["ack_type"] & NEEDS_ACK):
                self.insert_ack_request_id(meta["sender_address"], meta["packet_id"])

            return data

        return None

    def insert_ack_request_id(self, address, ack_id):
        # Acks are stored according to an address which asked for an ack
        buffer = self.ack_request_index.get(address)

        if not buffer:
            self.ack_request_index[address] = RingBuffer(10)

        self.ack_request_index[address].push(ack_id)
