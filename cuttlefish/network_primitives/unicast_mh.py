from .network import Network, IS_ACK, NEEDS_ACK
from cuttlefish.packet_management import attr

from cuttlefish.ring_buffer import RingBuffer, RingBufferUnderflow


class MultihopUnicast(Network):
    def __init__(self, address, routing_table, address_size=4, meta=None, buffer_size=10):
        super().__init__(address, address_size=address_size, meta=meta, buffer_size=buffer_size)

        self.routing_table = routing_table
        self.channel = None

        self.headers = (attr("intermediate_address", self.address_size, type="b"),
                        attr("dest_address", self.address_size, type="b"),
                        attr("origin_address", self.address_size, type="b")
                        )

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
        channel=None,
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

        self.channel = channel
        serializer.add_layer(headers=self.headers)

        self.ack_request_index = {} if ack else None

    def process_send(self, data, meta, *args, origin_address=None, ack_type=0,  **kwargs):
        dest_address = args[0]

        if ack_type & IS_ACK:
            buffer = self.ack_request_index.get(dest_address)

            try:
                self.next_ack_id = buffer.pop() if buffer else None
            except RingBufferUnderflow:
                ack_type = ack_type & 1
                pass

        super().process_send(data, meta, *args, ack_type=ack_type, **kwargs)

        intermediate_address = self.routing_table[dest_address]

        if origin_address:
            data.append([intermediate_address, dest_address, origin_address])
        else:
            data.append([intermediate_address, dest_address, self.address])

        return data

    def process_recv(self, data, meta, *args, **kwargs):
        address = data.pop()
        intermediate_address = address["intermediate_address"]
        dest_address = address["dest_address"]
        origin_address = address["origin_address"]

        meta.update({"origin_address": origin_address})

        data = super().process_recv(data, meta, *args, **kwargs)

        if not data:
            return None

        if dest_address == self.address:
            # print("Meta: {}".format(meta))
            if meta.get("ack_type") and (meta["ack_type"] & NEEDS_ACK):
                self.insert_ack_request_id(origin_address, meta["packet_id"])

            # print("Dest {} received {}".format(dest_address, data))
            return data
        elif intermediate_address == self.address:
            # print("Intermediate {} received {} for {}".format(intermediate_address, data, dest_address))
            # TODO: change this
            ack_type = meta.get("ack_type") if meta.get("ack_type") else 0
            ack_req_id = meta.get("ack_req_id") if meta.get("ack_req_id") else None
            packet_id = meta.get("packet_id") if meta.get("packet_id") else None
            # print("REQ ID: {}, ACK TYPE {}".format(ack_req_id, ack_type))
            self.channel.send([list(layer.values()) for layer in data], dest_address, origin_address=origin_address,
                              ack_type=ack_type, ack_req_id=ack_req_id, packet_id=packet_id)
        elif intermediate_address == self.promiscuous_address:
            # TODO: change this
            self.channel.send([list(layer.values()) for layer in data], self.promiscuous_address, ack_type=0)

    def insert_ack_request_id(self, address, ack_id):
        # Acks are stored according to an address which asked for an ack
        buffer = self.ack_request_index.get(address)

        if not buffer:
            self.ack_request_index[address] = RingBuffer(10)

        self.ack_request_index[address].push(ack_id)
