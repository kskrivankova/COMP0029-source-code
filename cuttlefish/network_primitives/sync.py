from .network import Network


class Synchronization(Network):
    def __init__(self, meta=None, buffer_size=10):
        super().__init__(meta=meta, buffer_size=buffer_size)

    def init_connection(
        self,
        socket,
        channel_id,
        foundry,
        orchestrator,
        scheduler,
        *args,
        mode=None,
        schedule_callback=None,
        recv_buffer_size=32,
        **kwargs
    ):

        return super().init_connection(
            socket,
            channel_id,
            foundry,
            orchestrator,
            scheduler,
            *args,
            channel=None,
            recv_buffer_size=recv_buffer_size,
            mode=mode,
            schedule_callback=schedule_callback,
            **kwargs,
        )

    def send(self, data, *args, **kwargs):
        pass

    def process(self, data, *args, **kwargs):
        pass