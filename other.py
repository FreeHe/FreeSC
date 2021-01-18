# ----------------------------------
# author : FreeHe
# Github : https://github.com/FreeHe
# ----------------------------------
# Description : 
# ---------------------------------
import os
import time
from subprocess import Popen, PIPE

from pyquery import PyQuery as p

from helium import *


def get_videos_url(url):
    print('get - ', url)
    if url.startswith('https://www.youtube.com/c') and url.endswith('videos'):
        print('start firefox ..')
        a = start_firefox(url, headless=False)
        size = len(a.page_source)
        scroll_down(1000)
        time.sleep(1)
        while size != len(a.page_source):
            size = len(a.page_source)
            scroll_down(2000)
            time.sleep(2)
            print(size)
        page = p(a.page_source)
        urls = [p(u).attr('href') for u in page('#video-title')]
        with open('urls.csv', 'w') as f:
            for u in urls:
                f.write(u + ',\n')
        print('收集到以下视频链接...\n')
        print(len(urls))
    else:
        print('err')
    kill_browser()


# get_videos_url("https://www.youtube.com/channel/UCADF1h8SBX1-iIW7ygRsuXQ/videos")


def c(idp, odp):
    for i in os.listdir(idp):
        if i.endswith('mp4') or i.endswith('avi'):
            p = Popen(
                ["C:\\Users\\84909\\Desktop\\teleV//ffmpeg.exe", "-c:v", "h264_cuvid", "-i", f"{idp + '//' + i}",
                 "-stream_loop", "-1", "-i", f"C://Users//84909//Desktop//TimeToLoveSC.mp3", "-filter_complex",
                 "[0:a][1:a]amix",
                 "-max_muxing_queue_size", "10000", "-vf", "scale=1920:1080", "-y", "-c:v", "hevc_nvenc",
                 odp + '//' + i], shell=False, stdout=PIPE, stderr=PIPE,
                stdin=PIPE)
            while p.poll() is None:
                out = p.stderr.readline().decode('utf8')
                print(out)
                if 'Qavg' in out:
                    time.sleep(1)
                    p.kill()
                    os.remove(idp + '//' + i)
            break

c('D:\\iqiyi\\视频共享\\下载的视频\\www.youtube.com', 'D:\\qq')
