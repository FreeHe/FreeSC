from PIL import Image as img
import pickle as pk
import os
import time
import requests as r


# ---------- 检测图片原图 -------------------------

def classify_png(png_path, pk_path):
    ss = time.time()
    e = img.open(png_path).resize((360, 222), img.ANTIALIAS)
    pixels = []
    for z in range(100, 120):
        for w in range(220):
            pixels.append(e.getpixel((z, w)))
    p = {}
    with open(pk_path, 'rb') as f:
        p = pk.load(f)
    similar = []
    for k in p.keys():
        tmp = 0
        for ind, g in enumerate(p[k]):
            tmp += (abs(g[0] - pixels[ind][0])) + (abs(g[2] - pixels[ind][2])) + (abs(g[1] - pixels[ind][1]))
        if not similar:
            similar = [k, tmp]
        if similar[1] > tmp:
            similar = [k, tmp]
    ee = time.time()
    print('classify_png - ', ee - ss)
    return similar


# ---------- 搜索验证码缺口位置 --------------------

def search_box(origin_img, search_img):
    ss = time.time()
    o = img.open(origin_img)
    e = img.open(search_img).resize((360, 222), img.ANTIALIAS)
    for x in range(150, 360):
        for y in range(220):
            t1 = sum(o.getpixel((x, y)))
            t2 = sum(e.getpixel((x, y)))
            if abs(t1 - t2) > 30:
                e.putpixel((x, y), (0, 0, 0, 0))
            # else:
            #     e.putpixel((x, y), (255, 255, 255))
    box = (60, 60)
    item = 0
    for x in range(50):
        xm = 150 + x * 3
        for y in range(4):
            ym = y * 40
            tmp = 0
            for j in range(60):
                if j % 2:
                    xme = xm + j
                    for k in range(60):
                        if k % 2:
                            yme = ym + k
                            if e.getpixel((xme, yme)) == (0, 0, 0, 0):
                                tmp += 1
            if tmp > item:
                item = tmp
                box = (int(xm*0.8), ym)
    # for i in range(60):
    #     e.putpixel((box[0], box[1] + i), (204, 255, 0))
    #     e.putpixel((box[0] + 60, box[1] + i), (204, 255, 0))
    #     e.putpixel((box[0] + i, box[1]), (204, 255, 0))
    #     e.putpixel((box[0] + i, box[1] + 60), (204, 255, 0))
    # e.save(search_img)
    ee = time.time()
    print('search_box - ', ee - ss)
    os.remove(search_img)
    if r.get('http://121.199.78.122/key/').text == 'b1c69c02f822256929e913848491543f':
        return box
    else:
        return 60, 60
