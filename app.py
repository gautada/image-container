#!/usr/bin/python
from fastapi import FastAPI, Request
from fastapi import File, UploadFile
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import starlette.status as status

from PIL import Image as PILImage

from pydantic import BaseModel

from os import listdir, remove
from os.path import isfile, join

# from pillow_heif import register_heif_opener

import base64
import io
import magic
import uvicorn
import time
import zlib

IMAGE_CACHE="/mnt/volumes/container/images"
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class Image(BaseModel):
	encimg: str

	@property
	def bytes(self):
		return base64.b64decode(self.encimg)
	
	@property	
	def mime(self):
		mime = magic.Magic(mime=True)
		return mime.from_buffer(self.bytes)
	
	@property
	def extension(self):
		return self.mime.split("/")[1]
	
	@property
	def format(self):
		return self.extension.upper()
			
	@property
	def name(self):
		return zlib.adler32(self.bytes)
		
	def write(self):
		tmp = self.bytes
		# if "image/heic" == self.mime:
		# 	register_heif_opener()
		# 	img = PILImage.open(io.BytesIO(tmp))
		# 	img_byte_arr = io.BytesIO()
		# 	img.save(img_byte_arr, format="PNG")
		# 	tmp = img_byte_arr.getvalue()	
		with open(f"{IMAGE_CACHE}/{self.name}", 'wb') as fw:
			fw.write(tmp)

	@classmethod
	def load(cls, name):
		tmp = None
		with open(f"{IMAGE_CACHE}/{name}", 'rb') as fr:
			tmp = base64.b64encode(fr.read())
		assert tmp is not None, "Image cannot be nil"
		return cls.parse_obj({"encimg":tmp})
	
	@staticmethod
	def  delete(name, group=None):
		remove(join(IMAGE_CACHE, name))
		
	@staticmethod
	def list(folder=None):
		rtn = []
		path = IMAGE_CACHE
		if folder is not None:
			path = join(path, folder)
		print(f"Path:{path}")
		imgs = [f for f in listdir(path) if isfile(join(path, f))]
		for img in imgs:
			if not img.endswith(('.DS_Store')):
				print(f"- Image: {img}")
				image = Image.load(img)
				rtn.append({"name":image.name,"mime":image.mime})
		return rtn


		
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
	return templates.TemplateResponse(request=request, name="index.html")

@app.get("/list", response_class=HTMLResponse)
def list(request: Request, group:str=None):
	limgs=[]
	rimgs=[]
	list = Image.list(folder=group)
	i = 1
	for item in list:
		if 0 < i % 2:
			limgs.append(item)
		else:
			rimgs.append(item)
		i += 1
	return templates.TemplateResponse(request=request, name="list.html", context={"limgs":limgs,"rimgs":rimgs,})

@app.get("/metadata/{name}", response_class=HTMLResponse)
def metadata(request: Request, name:str=None):
	img = Image.load(name)
	print( img.name )
	return templates.TemplateResponse(request=request, name="metadata.html", context={"img":img})

@app.get("/img/delete/{name}")
def delete(name:str):
	Image.delete(name)
	return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/img/src/{name}")
async def src(name:str):
	# time.sleep(10)
	img = Image.load(name)
	return Response(content=img.bytes, media_type=img.mime)

@app.get("/img/thumbnail/{name}")
def thumbnail(name:str):
	image = Image.load(name)
	img = PILImage.open(io.BytesIO(image.bytes))
	img.thumbnail((90,90))
	img_byte_arr = io.BytesIO()
	img.save(img_byte_arr, format=image.format)
	return Response(content=img_byte_arr.getvalue(), media_type=image.mime)

@app.get("/img/background/{name}")
def background(name:str):
	image = Image.load(name)
	img = PILImage.open(io.BytesIO(image.bytes))
	img.thumbnail((20,20), PILImage.Resampling.LANCZOS)
	img_byte_arr = io.BytesIO()
	img.save(img_byte_arr, format=image.format)
	return Response(content=img_byte_arr.getvalue(), media_type=image.mime)


		

		
# https://www.tutorialspoint.com/python_pillow/python_pillow_creating_thumbnails.htm

@app.put("/push")
def push(image: Image):
	# print( image.mime() )
	image.write()
	return {"done":"ok"}


@app.get("/upload", response_class=HTMLResponse)
def read_root():
	content = '''
	<body>
	<form action='/upload' enctype='multipart/form-data' method='post'>
	<input name='file' type='file'>
	<input type='submit'>
	</form>
	</body>
	'''
	return content

@app.post("/upload")
def upload(file: UploadFile = File(...)):
	try:
		contents = file.file.read()
		with open(file.filename, 'wb') as f:
			f.write(contents)
	except Exception:
		return {"message": "There was an error uploading the file"}
	finally:
		file.file.close()

	return {"message": f"Successfully uploaded {file.filename}"}


if "__main__"==__name__:
	uvicorn.run(
		"app:app",
		host="0.0.0.0",
		port=8080,
		log_level="debug",
		reload=True
	)
	

	