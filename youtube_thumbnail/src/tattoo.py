import cv2, numpy as np, json, sys
P=cv2.imread('person.png',cv2.IMREAD_UNCHANGED)   # BGRA cutout
rgb=P[...,:3].astype(np.float32); alpha=P[...,3]
H,W=alpha.shape
def ink_map(img,k=17,gain=2.2,thr=0.04):
    L=cv2.cvtColor(img,cv2.COLOR_BGR2LAB)[...,0].astype(np.float32)
    env=cv2.morphologyEx(L,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    env=cv2.GaussianBlur(env,(0,0),k/3)
    ink=(env-L)/np.maximum(env,1)
    return np.clip((ink-thr)*gain,0,1)
srcs={n:cv2.imread(n+'.jpg') for n in ['tat1','tat2']}
inks={n:ink_map(im) for n,im in srcs.items()}
cfg=json.load(open('tattoo_cfg.json'))
# ---------- skin mask ----------
blur=cv2.GaussianBlur(rgb,(0,0),5)
skin=((blur[...,2]>38)&(blur[...,2]>blur[...,0]*1.08)&(alpha>200)).astype(np.uint8)
region=np.zeros((H,W),np.uint8)
for poly in cfg['regions']: cv2.fillPoly(region,[np.array(poly,np.int32)],1)
for poly in cfg['exclude']: cv2.fillPoly(region,[np.array(poly,np.int32)],0)
m=(skin&region)
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
m=cv2.erode(m,np.ones((5,5),np.uint8))
mf=cv2.GaussianBlur(m.astype(np.float32),(0,0),2.0)
# ---------- clean skin ----------
lab=cv2.cvtColor(rgb.astype(np.uint8),cv2.COLOR_BGR2LAB).astype(np.float32)
L=lab[...,0]
k=cfg.get('close',61)
Lc=L.copy(); Lc[region==0]=0
env=cv2.morphologyEx(L,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
env=cv2.GaussianBlur(env,(0,0),k/4)
oldink=np.clip(((env-L)/np.maximum(env,1)-0.03)*3,0,1)
inkpix=((oldink>0.12)&(m>0)).astype(np.uint8)
ab=lab[...,1:].copy()
for c in range(2):
    ch=np.clip(ab[...,c],0,255).astype(np.uint8)
    ch=cv2.inpaint(ch,inkpix,7,cv2.INPAINT_TELEA)
    ab[...,c]=cv2.GaussianBlur(ch.astype(np.float32),(0,0),9)
Lbase=env*cfg.get('Lscale',0.97)
rng=np.random.default_rng(1)
noise=cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),0.7)*3.0+cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),4)*6.0
clean=np.dstack([np.clip(Lbase+noise,0,255),ab]).astype(np.uint8)
clean=cv2.cvtColor(clean,cv2.COLOR_LAB2BGR).astype(np.float32)
# ---------- new ink ----------
newink=np.zeros((H,W),np.float32)
for seg in cfg['segments']:
    s=np.float32(seg['src']); d=np.float32(seg['dst'])
    M=cv2.getPerspectiveTransform(s,d)
    if seg.get('mode')=='hp':
        Ls=cv2.cvtColor(srcs[seg['img']],cv2.COLOR_BGR2LAB)[...,0].astype(np.float32)
        sg=seg.get('sigma',4)
        hp=cv2.GaussianBlur(Ls,(0,0),sg)-Ls
        ink=np.clip((hp-1.5)/(sg*2.2),0,1)
    else:
        ink=inks[seg['img']].copy()
    sm=np.zeros(ink.shape,np.uint8); cv2.fillPoly(sm,[np.int32(seg.get('srcmask',seg['src']))],1)
    sm=cv2.GaussianBlur(sm.astype(np.float32),(0,0),4)
    if seg.get('hp',0):
        ink=np.clip(ink-cv2.GaussianBlur(ink,(0,0),seg['hp'])*0.8,0,1)*1.6
    ink=ink*sm*seg.get('gain',1.0)
    w=cv2.warpPerspective(ink,M,(W,H),flags=cv2.INTER_CUBIC)
    newink=np.maximum(newink,np.clip(w,0,1)); cv2.imwrite(f"dbg_w{cfg['segments'].index(seg)}.png",(255-np.clip(w,0,1)*255).astype(np.uint8)[380:941,380:1300])
newink=np.clip(newink*cfg.get('inkgain',1.35),0,1)
newink=cv2.GaussianBlur(newink,(0,0),0.6)
tint=np.array(cfg.get('tint',[0.42,0.38,0.34]),np.float32)  # BGR multiply at full ink
mult=1-newink[...,None]*(1-tint)
tat=clean*mult
out=rgb*(1-mf[...,None])+tat*mf[...,None]
res=P.copy(); res[...,:3]=np.clip(out,0,255).astype(np.uint8)
cv2.imwrite('person_tat.png',res)
cv2.imwrite('dbg_clean.png',np.clip(rgb*(1-mf[...,None])+clean*mf[...,None],0,255).astype(np.uint8))
cv2.imwrite('dbg_mask.png',(mf*255).astype(np.uint8))
