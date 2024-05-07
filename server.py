from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from pydantic import BaseModel

# Define the SQLAlchemy model
Base = declarative_base()

class CarDetails(Base):
    __tablename__ = "car_details"
    id = Column(Integer, primary_key=True, index=True)
    license_plate_number = Column(String, index=True)
    car_type = Column(String)
    car_make = Column(String)
    car_color = Column(String)
    time_of_detection = Column(DateTime)
    site = Column(String)
    image_path = Column(String)

class Site(Base):
    __tablename__ = "site_details"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    state = Column(String, index=True)
    city = Column(String, index=True)

# Configure the SQLAlchemy engine and create tables
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI()


# Configure templates
templates = Jinja2Templates(directory="templates")

# Mount a static directory to serve images
app.mount("/images", StaticFiles(directory="images"), name="images")

app.mount("/assets/", StaticFiles(directory="assets"), name="assets")

# Pydantic model for request payload
class CarDetailsRequest(BaseModel):
    license_plate_number: str
    car_type: str
    car_make: str
    car_color: str
    time_of_detection: datetime
    site: str

class SiteDetailsRequest(BaseModel):
    name: str
    city: str
    state: str
    
class SiteDetailsResponse(BaseModel):
    id: int
    name: str
    city: str
    state: str


class CarDetailsResponse(BaseModel):
    id: int
    license_plate_number: str
    car_type: str
    car_make: str
    car_color: str
    time_of_detection: datetime
    site: str
    image_path: str

class Filter(BaseModel):
    license_plate_number: str
    site: str
    car_make: str
    car_type: str

# Endpoint to save car details
@app.post("/save_car_details")
async def save_car_details(
    file: UploadFile = File(...),
    license_plate_number: str = Form(...),
    car_type: str = Form(...),
    car_make: str = Form(...),
    car_color: str = Form(...),
    time_of_detection: datetime = Form(...),
    site: str = Form(...),
):
    # Save the image to a folder or cloud storage (you can customize this part)
    image_path = f"./images/{file.filename}"
    with open(image_path, "wb") as image:
        image.write(file.file.read())

    # Create an instance of the CarDetails model
    car_details = CarDetails(
        license_plate_number=license_plate_number,
        car_type=car_type,
        car_make=car_make,
        car_color=car_color,
        time_of_detection=time_of_detection,
        site=site,
        image_path = image_path
    )

    # Open a database session and add the car details
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    db.add(car_details)
    db.commit()
    db.refresh(car_details)

    return JSONResponse(content={"message": "Car details saved successfully"}, status_code=201)

@app.post("/save_site_details")
async def save_site_details(site_details: SiteDetailsRequest):
    site =  Site(name = site_details.name, state = site_details.state, city = site_details.city)

    # Open a database session and add the car details
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    db.add(site)
    db.commit()
    db.refresh(site)

    return JSONResponse(content={"message": "site details saved successfully"}, status_code=201)
    
@app.get("/get_sites")
async def get_sites(request: Request):
    # Open a database session and retrieve all car details
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    sites = db.query(Site).all()

    # Close the database session
    db.close()

    sites_response = [
        SiteDetailsResponse(
            id=site.id,
            name= site.name,
            city= site.name,
            state= site.state
        ) for site in sites
    ]

    return templates.TemplateResponse("sites_table.html", {"request": request, "sites": sites})

@app.get("/get_site/{site_id}")
async def get_site(site_id: int, request: Request):
    # Open a database session and retrieve all car details
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    site = db.query(Site).filter(Site.id == site_id).first()
    
    cars = db.query(CarDetails).filter(CarDetails.site == site.name).all()

    db.close()

    cars_with_paths = [
        CarDetailsResponse(
            id=car.id,
            license_plate_number=car.license_plate_number,
            car_type=car.car_type,
            car_make=car.car_make,
            car_color=car.car_color,
            time_of_detection=car.time_of_detection,
            site=car.site,
            image_path=car.image_path,  # Adjust file extension if needed
        )
        for car in cars
    ]

    return templates.TemplateResponse("site_page.html", {"request": request, "site": site, "cars": cars_with_paths})

@app.get("/create_site")
async def create_site_page(request: Request):
    return templates.TemplateResponse("create_site.html", {"request" : request})
# Endpoint to retrieve and display car details in an HTML table
@app.get("/car_details_table")
async def car_details_table(request: Request):
    # Open a database session and retrieve all car details
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    cars = db.query(CarDetails).all()

    # Close the database session
    db.close()

    # Create a list of CarDetailsResponse objects with image paths
    cars_with_paths = [
        CarDetailsResponse(
            id=car.id,
            license_plate_number=car.license_plate_number,
            car_type=car.car_type,
            car_make=car.car_make,
            car_color=car.car_color,
            time_of_detection=car.time_of_detection,
            site=car.site,
            image_path=car.image_path,  # Adjust file extension if needed
        )
        for car in cars
    ]

    # Render the HTML template with the retrieved car details
    return templates.TemplateResponse("cars_table.html", {"request": request, "cars": cars_with_paths})


@app.get("/car_detections/{license_plate_number}")
async def get_car_detections(license_plate_number: str, request: Request):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    # Retrieve all detections with the specified license_plate_number
    detections = db.query(CarDetails).filter(
        CarDetails.license_plate_number == license_plate_number
    ).order_by(CarDetails.time_of_detection).all()

    db.close()
    # Convert detections to a list of dictionaries
    print(detections)
    for det in detections:
        print(det.car_make)
    detections_list = [
        {
            "car_type": detection.car_type,
            "car_make": detection.car_make,
            "car_color": detection.car_color,
            "time_of_detection": detection.time_of_detection,
            "site": detection.site,
            "image_path": detection.image_path
        }
        for detection in detections
    ]

    return templates.TemplateResponse("profile.html", {"request": request, "cars": detections, "license_plate_number": license_plate_number})
    # return {"license_plate_number": license_plate_number, "detections": detections_list}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return HTMLResponse(content=open("templates/index.html").read(), status_code=200)


@app.post("/car_details/download_csv")
async def download_csv(filters: Filter):

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    # Build the filter conditions for the database query
    filter_conditions = {key: value for key, value in filters.dict().items() if (value is not None and value != "")}



    # Apply filters to query the data from the database
    filtered_cars = db.query(CarDetails).filter_by(**filter_conditions).all()

    # Create a CSV file with the filtered data
    csv_data = [['License Plate', 'Car Type', 'Car Make', 'Car Color', 'Time of Detection', 'Site']]
    for car in filtered_cars:
        csv_data.append([car.license_plate_number, car.car_type, car.car_make, car.car_color, car.time_of_detection, car.site])

    # Create a generator function to stream the CSV file
    def generate_csv():
        for row in csv_data:
            yield ','.join(map(str, row)) + '\n'

    # Return the CSV file as a streaming response
    return StreamingResponse(
        generate_csv(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="filtered_data.csv"'}
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)