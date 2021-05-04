import time

try:
    from machine import Timer
except Exception:
    pass


def asynchronous_schedule(
    scheduler, channel_id, uplink_interval=2, downlink_interval=2, uplink_downlink_interval=1, **kwargs
):
    uplink_alarm = Timer.Alarm(
        scheduler.uplink, uplink_interval, periodic=True, arg=(scheduler, channel_id, kwargs)
    )
    time.sleep(uplink_downlink_interval)
    downlink_alarm = Timer.Alarm(
        scheduler.downlink, downlink_interval, periodic=True, arg=(scheduler, kwargs)
    )

    return uplink_alarm, downlink_alarm


def synchronous_schedule(scheduler, channel_id, **kwargs):
    """
    Synchronous schedule: uplink and downlink executed upon calling channel.send and channel.receive respectively
    """

    def initiate_transmission():
        return scheduler.uplink((scheduler, channel_id, kwargs))

    def initiate_receive():
        return scheduler.downlink((scheduler, kwargs))

    return initiate_transmission, initiate_receive


def implicitly_synchronous_schedule(scheduler, channel_id, receive_delay=0.00002, rx1=1, rx2=2, **kwargs):
    """
    LoRaWAN-like schedule
    """

    def initiate_transmission_window():
        scheduler.uplink((scheduler, channel_id, kwargs))
        time.sleep(receive_delay)

        timer = Timer.Chrono()
        timer.start()

        result = recv_window(timer, rx1, scheduler.downlink, (scheduler, kwargs))

        if not result:
            timer.reset()
            recv_window(timer, rx2, scheduler.downlink, (scheduler, kwargs))

        timer.stop()

    return initiate_transmission_window, None


def recv_window(timer, window_length, downlink, arg):
    result = False

    while timer.read() < window_length:
        result = downlink(arg)

        if result:
            timer.stop()
            return result

        time.sleep(0.001)

    return result


def implicitly_synchronous_schedule_gateway(scheduler, channel_id, **kwargs):
    def initiate_gateway_send_mode():
        scheduler.uplink((scheduler, channel_id, kwargs))

    def initiate_gateway_recv_mode():
        scheduler.downlink((scheduler, kwargs))

    return initiate_gateway_send_mode, initiate_gateway_recv_mode
