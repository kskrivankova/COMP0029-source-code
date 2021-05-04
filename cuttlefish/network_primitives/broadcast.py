from .network import Network


class Broadcast(Network):
    def __init__(self, address, meta=None, buffer_size=10,):
        super().__init__(address, meta=meta, buffer_size=buffer_size)

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
        return super().init_connection(
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
