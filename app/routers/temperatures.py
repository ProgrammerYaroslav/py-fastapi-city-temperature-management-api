from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from .. import crud, schemas, database, models

router = APIRouter(
    prefix="/temperatures",
    tags=["temperatures"]
)

@router.post("/update", response_model=List[schemas.TemperatureResponse])
async def update_temperatures(db: Session = Depends(database.get_db)):
    """
    Fetches current temperature for all cities in the DB and saves them.
    Uses Open-Meteo API.
    """
    cities = crud.get_cities(db, limit=1000)
    updated_records = []
    
    async with httpx.AsyncClient() as client:
        for city in cities:
            try:
                # 1. Geocode the city name to get lat/lon
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city.name}&count=1&language=en&format=json"
                geo_resp = await client.get(geo_url)
                geo_data = geo_resp.json()
                
                if not geo_data.get("results"):
                    print(f"Could not find coordinates for {city.name}")
                    continue
                    
                lat = geo_data["results"][0]["latitude"]
                lon = geo_data["results"][0]["longitude"]

                # 2. Fetch temperature using lat/lon
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                weather_resp = await client.get(weather_url)
                weather_data = weather_resp.json()
                
                current_temp = weather_data["current_weather"]["temperature"]
                
                # 3. Save to DB
                record = crud.create_temperature(db, city.id, current_temp)
                updated_records.append(record)
                
            except Exception as e:
                print(f"Error updating {city.name}: {str(e)}")
                # Continue to next city even if one fails
                continue

    if not updated_records:
        raise HTTPException(status_code=404, detail="No weather data updated. Check city names or internet connection.")

    return updated_records

@router.get("/", response_model=List[schemas.TemperatureResponse])
def read_temperatures(
    city_id: Optional[int] = None, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    return crud.get_temperatures(db, city_id=city_id, skip=skip, limit=limit)
