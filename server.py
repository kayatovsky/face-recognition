import asyncio
from rofl import ROFL
import api
import datetime as dt

rofl = ROFL("trained_knn_model.clf", retina=True, emotions=True)
room = "305"
hour_range = [str(i) if i > 9 else "0" + str(i) for i in range(8,22)]
rofl_folder = "14Xsw4xk6vUFINsyy1OH5937Rq98W4JHw"


async def watch_drive():
    now = dt.datetime.now()
    if now.strftime("%M") == "00" or now.strftime("%M") == "30":
        hour = now.strftime("%H") if now.strftime("%M") == "00" else str(now.hour - 1)
        hour = "0" + hour if int(hour) < 10 else hour
        hour = "23" if int(hour) < 0 else hour
        minute = "00" if now.strftime("%M") == "30" else "30"
        date = now.strftime("%Y-%m-%d")
        filename = api.download_video_nvr(room, date, hour + ":" + minute)
        rofl.update_queue(filename)
        return filename
    return 0


async def watch_drive_in_range():
    now = dt.datetime.now()
    date = now.strftime("%Y-%m-%d")
    for hour in hour_range:
        filename = await ioloop.run_in_executor(None, api.download_video_nvr, room, date, hour + ":00")
        rofl.update_queue(filename)
        filename = await ioloop.run_in_executor(None, api.download_video_nvr, room, date, hour + ":30")
        rofl.update_queue(filename)
    return 0


async def recognize():
    if len([line.strip() for line in open("queue.txt")]) > 0:
        filename = await rofl.async_run_from_queue(ioloop, fps_factor=60, emotions=True)
        api.upload_video(filename, upload_name=filename.split('/')[-1], folder_id=rofl_folder)
        api.upload_video(filename, upload_name=filename, room_num=room)
        return filename
    else:
        await asyncio.sleep(5)
        return 0

async def asynchronous(futures):
    for i, future in enumerate(asyncio.as_completed(futures)):
        result = await future
    return 0


# vid, results = api.download_video_nvr('504', '2020-07-12', '12:00')
# rofl.update_queue(vid)
ioloop = asyncio.get_event_loop()

# asyncio.ensure_future(watch_drive())
# futures = [watch_drive_in_range(), see_emotions()]
# asyncio.ensure_future(watch_drive_in_range())
asyncio.ensure_future(watch_drive_in_range())
asyncio.ensure_future(recognize())
# asyncio.ensure_future(asynchronous(futures))
ioloop.run_forever()

# ioloop.run_until_complete(asynchronous())

ioloop.close()
