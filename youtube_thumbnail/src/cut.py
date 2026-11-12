from rembg import remove, new_session
from PIL import Image
im=Image.open('thumbnail.png').convert('RGB')
s=new_session('birefnet-portrait')
out=remove(im,session=s)
out.save('person.png')
