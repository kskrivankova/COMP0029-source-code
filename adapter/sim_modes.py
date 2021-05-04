import _thread
import time


def asynchronous_schedule_sim(
    scheduler,
    channel_id,
    uplink_interval=2,
    downlink_interval=2,
    uplink_downlink_interval=1,
    **kwargs
):
    cancel_flag = False

    _thread.start_new_thread(
        alarm, (uplink_interval, cancel_flag, scheduler.uplink, [scheduler, channel_id, kwargs])
    )
    time.sleep(uplink_downlink_interval)
    _thread.start_new_thread(
        alarm,
        (
            downlink_interval,
            cancel_flag,
            scheduler.downlink,
            [scheduler, kwargs],
        ),
    )

    return cancel_flag


def alarm(interval, cancel_flag, callback, arg):
    while True:
        if cancel_flag:
            break

        time.sleep(interval)
        callback(arg)


def implicitly_synchronous_schedule_sim(scheduler, channel_id, receive_delay=0.00003, window_length=2, **kwargs):
    """
    LoRaWAN-like schedule
    """

    def initiate_transmission_window():
        scheduler.uplink((scheduler, channel_id, kwargs))
        time.sleep(receive_delay)

        time_0 = time.time()

        result = recv_window(time_0, window_length, scheduler.downlink, (scheduler, kwargs))

        if not result:
            time_0 = time.time()
            recv_window(time_0, window_length, scheduler.downlink, (scheduler, kwargs))

    return initiate_transmission_window, None


def recv_window(time_0, window_length, downlink, arg):
    result = False

    while (time.time() - time_0) < window_length:
        result = downlink(arg)

        if result:
            return result

    return result
