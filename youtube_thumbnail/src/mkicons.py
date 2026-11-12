from PIL import Image, ImageFilter, ImageDraw
import numpy as np
ref=Image.open('reference.jpg').convert('RGB')
boxes={'tokenomist':(43,120,119,196),'defillama':(43,233,119,309),'coinglass':(43,347,119,423)}
S=1024
for name,b in boxes.items():
    c=ref.crop(b).resize((S,S),Image.LANCZOS).filter(ImageFilter.GaussianBlur(S/76*0.9))
    a=np.array(c).astype(float)
    yy,xx=np.mgrid[0:S,0:S]; cx=cy=(S-1)/2; r=S/2-S*0.012
    dist=np.hypot(xx-cx,yy-cy)
    inside=dist<r*0.97
    # sample circle color: ring at 0.9r
    ring=(dist>r*0.80)&(dist<r*0.9)
    pix=a[ring]
    lum=pix.sum(1)
    if name=='coinglass':
        base=np.median(pix[lum<200],0)
    else:
        base=np.median(pix[lum<650],0)
    white=np.array([255,255,255.])
    palette=[base,white]
    if name=='coinglass':
        palette.append(np.array([240,150,40.]))
    P=np.array(palette)
    d=((a[:,:,None,:]-P[None,None])**2).sum(-1)
    lab=d.argmin(-1)
    lab[~inside]=0
    if name=='coinglass':
        cd=np.hypot(xx-cx-S*0.04,yy-cy)
        lab[(lab==2)&(cd>r*0.33)]=0
        lab[(lab==1)&(cd<r*0.22)]=2
    # build layers with smoothing to antialias
    out=np.zeros((S,S,4))
    for i,col in enumerate(P):
        m=Image.fromarray(((lab==i)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
        m=np.array(m)/255.
        out[...,:3]+=m[...,None]*col
    out[...,:3]=np.clip(out[...,:3],0,255)
    circ=Image.new('L',(S,S),0); ImageDraw.Draw(circ).ellipse((S*0.012,S*0.012,S-S*0.012,S-S*0.012),fill=255)
    out[...,3]=np.array(circ)
    im=Image.fromarray(out.astype(np.uint8),'RGBA').resize((256,256),Image.LANCZOS)
    im.save(f'icons/{name}.png'); print(name,base)
