from amadeus import Client, ResponseError
from services.parse_booking import parse_flight, parse_hotel
from setups import AMADEUS_API, AMADEUS_SECRET

class AmadeusBookingEngine:
    def __init__(self):
        self.amadeus = Client(
            client_id=AMADEUS_API,
            client_secret=AMADEUS_SECRET
        )
    
    def get_iata(self, city_name):
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=city_name,
                subType='CITY'
            )
            return response.data[0].get('iataCode')
        except ResponseError as error:
            return f"[ERROR]: {error}"
    
    def check_iata(self, code):
        return isinstance(code, str) and len(code) == 3 and code.isalpha() and code.isupper()

    def search_flights(self, origin, destination, departure_date, adults=1):
        if not self.check_iata(origin):
           origin = self.get_iata(origin)
           print(f"Origin IATA code converted: {origin}")
        if not self.check_iata(destination):
            destination = self.get_iata(destination)
            print(f"Destination IATA code converted: {destination}")
        try:
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=adults
            )

            return parse_flight(response.data[:3])
        except ResponseError as error:
            return f"An error occurred: {error}"
    
    def search_hotels(self, city_code, check_in_date, check_out_date, adults=1):
        if not self.check_iata(city_code):
            city_code = self.get_iata(city_code)
            print(f"City IATA code converted: {city_code}")
        try:
            hotels_by_city = self.amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code)
            hotelIds = [hotel.get('hotelId') for hotel in hotels_by_city.data[:3]]

            # Hotel Search API to get list of offers for a specific hotel
            response = self.amadeus.shopping.hotel_offers_search.get(
                hotelIds=hotelIds, adults=adults, checkInDate=check_in_date, checkOutDate=check_out_date)
            
            return parse_hotel(response.data[:3]) 
        except ResponseError as error:
            return f"An error occurred: {error}"
