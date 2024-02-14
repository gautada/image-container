#!/usr/bin/python
from fastapi import FastAPI, Request
from fastapi import File, UploadFile
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image as PILImage

from pydantic import BaseModel

from os import listdir
from os.path import isfile, join

# from pillow_heif import register_heif_opener

import base64
import io
import magic
import uvicorn
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
				rtn.append({"id":image.name,"mime":image.mime})
		return rtn


		
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
	return templates.TemplateResponse(request=request, name="index.html")

@app.get("/list", response_class=HTMLResponse)
def list(request: Request, group: str=None):
	list = Image.list(folder=group)
	for item in list:
		print( item )
	return templates.TemplateResponse(request=request, name="list.html", context={"list":list})

@app.get("/img/src/{id}")
def image(id:str):
	img = Image.load(id)
	return Response(content=img.bytes, media_type=img.mime)

@app.get("/img/tn/{id}")
def image(id:str):
	image = Image.load(id)
	img = PILImage.open(io.BytesIO(image.bytes))
	img.thumbnail((90,90))
	img_byte_arr = io.BytesIO()
	img.save(img_byte_arr, format=image.format)
	return Response(content=img_byte_arr.getvalue(), media_type=image.mime)
			
	# img_byte_arr = io.BytesIO()
	# with Img.open("/mnt/volumes/container/2056145448") as img:
	# 	img.save(img_byte_arr, format='PNG')
	# return img_byte_arr.getvalue()
	# 
	# image_bytes: bytes = generate_cat_picture()
	# # media_type here sets the media type of the actual response sent to the client.
	# return Response(content=img_byte_arr.getvalue(), media_type="image/png")


	

		

		
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
		app,
		host="0.0.0.0",
		port=8080,
		log_level="debug",
	)
	

	