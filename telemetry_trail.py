#!/usr/bin/env python3

import argparse, io, math, os, re, subprocess, sys
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

TILE = 256
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
USER_AGENT = "Telemetry-Overlay/1.0"
CACHE = Path("tile_cache")

def gps_pair(s):
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", str(s))
    if len(nums) < 2: return None
    a,b = float(nums[0]), float(nums[1])
    if abs(a) < 1e-10 and abs(b) < 1e-10: return None
    return a,b

def mercator(lat, lon, z):
    lat = max(-85.05112878, min(85.05112878, lat))
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n * TILE
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1+s)/(1-s))/(4*math.pi)) * n * TILE
    return x,y

def tile_image(z, x, y):
    n = 2 ** z
    x %= n
    if y < 0 or y >= n:
        return Image.new("RGB",(TILE,TILE),(30,30,30))
    p = CACHE / str(z) / str(x) / f"{y}.jpg"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        req = Request(ESRI.format(z=z,x=x,y=y), headers={"User-Agent":USER_AGENT})
        try:
            with urlopen(req, timeout=20) as r:
                p.write_bytes(r.read())
        except Exception as e:
            print(f"\nTile download failed {z}/{x}/{y}: {e}")
            return Image.new("RGB",(TILE,TILE),(45,45,45))
    return Image.open(p).convert("RGB")

def map_crop(lat, lon, z, size):
    px,py = mercator(lat,lon,z)
    left,top = px-size/2, py-size/2
    tx0,ty0 = math.floor(left/TILE), math.floor(top/TILE)
    tx1,ty1 = math.floor((left+size)/TILE), math.floor((top+size)/TILE)
    canvas = Image.new("RGB",((tx1-tx0+1)*TILE,(ty1-ty0+1)*TILE))
    for ty in range(ty0,ty1+1):
        for tx in range(tx0,tx1+1):
            canvas.paste(tile_image(z,tx,ty),((tx-tx0)*TILE,(ty-ty0)*TILE))
    ox = int(left-tx0*TILE); oy=int(top-ty0*TILE)
    return canvas.crop((ox,oy,ox+size,oy+size))

def font(size):
    for f in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if Path(f).exists(): return ImageFont.truetype(f,size)
    return ImageFont.load_default()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="fpv_minimap.mp4")
    ap.add_argument("--start", type=float, default=0, help="seconds from first valid GPS point")
    ap.add_argument("--duration", type=float, default=30, help="seconds; use 0 for full log")
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--zoom", type=int, default=15)
    ap.add_argument("--trail", type=float, default=45,
                    help="legacy option; route is now persistent from render start")
    args=ap.parse_args()

    df=pd.read_csv(args.csv)
    if "GPS" not in df: sys.exit("CSV has no GPS column")
    pairs=df["GPS"].apply(gps_pair)
    df["lat"]=[p[0] if p else np.nan for p in pairs]
    df["lon"]=[p[1] if p else np.nan for p in pairs]
    df=df.dropna(subset=["lat","lon"]).copy()
    if df.empty: sys.exit("No valid GPS fixes")

    # EdgeTX Date + Time, preserving fractional seconds.
    df["dt"]=pd.to_datetime(df["Date"].astype(str)+" "+df["Time"].astype(str), errors="coerce")
    df=df.dropna(subset=["dt"]).sort_values("dt")
    t0=df["dt"].iloc[0]
    df["sec"]=(df["dt"]-t0).dt.total_seconds()
    end=float(df["sec"].iloc[-1])
    start=max(0,args.start)
    duration=(end-start) if args.duration<=0 else min(args.duration,end-start)
    if duration<=0: sys.exit("Requested interval is outside the log")

    # Home = first valid fix. Altitude in EdgeTX GAlt is normally relative-to-home in this log.
    hlat,hlon=float(df["lat"].iloc[0]),float(df["lon"].iloc[0])
    def hav(lat,lon):
        R=6371000
        p1,p2=math.radians(hlat),math.radians(lat)
        dp=math.radians(lat-hlat); dl=math.radians(lon-hlon)
        a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2*R*math.asin(math.sqrt(a))
    df["home_m"]=[hav(a,b) for a,b in zip(df.lat,df.lon)]

    cols = {c:c for c in df.columns}
    speed="GSpd(kmh)" if "GSpd(kmh)" in cols else None
    alt="GAlt(m)" if "GAlt(m)" in cols else None
    lq="RQly(%)" if "RQly(%)" in cols else None

    # Interpolate numeric telemetry to video frame times.
    ts=df["sec"].to_numpy(float)
    latv=df["lat"].to_numpy(float); lonv=df["lon"].to_numpy(float)
    spdv=pd.to_numeric(df[speed],errors="coerce").interpolate().bfill().ffill().to_numpy() if speed else np.zeros(len(df))
    altv=pd.to_numeric(df[alt],errors="coerce").interpolate().bfill().ffill().to_numpy() if alt else np.zeros(len(df))
    lqv=pd.to_numeric(df[lq],errors="coerce").interpolate().bfill().ffill().to_numpy() if lq else np.zeros(len(df))
    homev=df["home_m"].to_numpy(float)

    W=H=args.size
    cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
         "-r",str(args.fps),"-i","-","-an","-c:v","libx264","-preset","veryfast",
         "-crf","20","-pix_fmt","yuv420p",args.out]
    try:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("FFmpeg not found in PATH. Open a new CMD after installing FFmpeg.")

    fbig=font(24); fsmall=font(17)
    total=max(1,int(duration*args.fps))
    for k in range(total):
        t=start+k/args.fps
        lat=float(np.interp(t,ts,latv)); lon=float(np.interp(t,ts,lonv))
        im=map_crop(lat,lon,args.zoom,args.size)
        d=ImageDraw.Draw(im,"RGBA")

        # Trail: convert previous positions to pixels relative to current map center.
        cx,cy=mercator(lat,lon,args.zoom)
        # Persistent route: draw every GPS point flown from the start up to now.
        mask=(ts>=start)&(ts<=t)
        pts=[]
        for la,lo in zip(latv[mask],lonv[mask]):
            x,y=mercator(float(la),float(lo),args.zoom)
            pts.append((W/2+x-cx,H/2+y-cy))
        if len(pts)>1:
            d.line(pts, fill=(255,70,40,230), width=5)

        # Home marker and line when on-screen.
        hx,hy=mercator(hlat,hlon,args.zoom)
        hp=(W/2+hx-cx,H/2+hy-cy)
        if -20<hp[0]<W+20 and -20<hp[1]<H+20:
            d.ellipse((hp[0]-7,hp[1]-7,hp[0]+7,hp[1]+7),fill=(80,180,255,255),outline=(255,255,255,255),width=2)

        # Aircraft marker in center: simple yellow dot (no heading implied).
        c=W/2
        r=9
        d.ellipse((c-r,c-r,c+r,c+r), fill=(255,230,30,255),
                  outline=(0,0,0,255), width=3)

        sp=float(np.interp(t,ts,spdv)); al=float(np.interp(t,ts,altv))
        l=float(np.interp(t,ts,lqv)); hm=float(np.interp(t,ts,homev))
        # Readable telemetry panel.
        d.rounded_rectangle((10,H-92,W-10,H-10),radius=12,fill=(0,0,0,155))
        d.text((24,H-82),f"{sp:4.0f} km/h",font=fbig,fill="white")
        d.text((W//2+5,H-82),f"ALT {al:4.0f} m",font=fbig,fill="white")
        d.text((24,H-47),f"HOME {hm/1000:.2f} km",font=fsmall,fill="white")
        d.text((W//2+5,H-47),f"LQ {l:.0f}%",font=fsmall,fill="white")

        proc.stdin.write(np.asarray(im,dtype=np.uint8).tobytes())
        if k % max(1,args.fps*5)==0:
            print(f"\rRendering {k/args.fps:.0f}/{duration:.0f}s",end="",flush=True)

    proc.stdin.close()
    rc=proc.wait()
    print()
    if rc: sys.exit(f"FFmpeg failed with exit code {rc}")
    print(f"Done: {args.out}")
    print(f"Telemetry start: {t0} | rendered log offset {start:.1f}s for {duration:.1f}s")

if __name__=="__main__":
    main()
