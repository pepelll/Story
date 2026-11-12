from PIL import Image, ImageFilter
import numpy as np
bg=Image.open('thumbnail.png').convert('RGBA')
cards=Image.open('cards.png').convert('RGBA')
person=Image.open('person.png').convert('RGBA')
# slight alpha choke to avoid halo from old card colors
a=person.getchannel('A').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
person.putalpha(a)
out=bg.copy(); out.alpha_composite(cards); out.alpha_composite(person)
out=out.convert('RGB'); out.save('thumbnail_new.png')
out.resize((1280,720),Image.LANCZOS).save('preview_1280.png')
out.resize((320,180),Image.LANCZOS).save('preview_320.png')
