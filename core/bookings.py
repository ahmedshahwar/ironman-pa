from amadeus import Client, ResponseError
from services.parse_booking import parse_flight, parse_hotel
from setups import AMADEUS_API, AMADEUS_SECRET

class AmadeusBookingEngine:
    def __init__(self):
        self.amadeus = Client(
            client_id=AMADEUS_API,
            client_secret=AMADEUS_SECRET
        )
    
    def search_flights(self, origin, destination, departure_date, adults=1):
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
        try:

            hotels_by_city = self.amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code)
            hotelIds = [hotel.get('hotelId') for hotel in hotels_by_city.data[:3]]

            # Hotel Search API to get list of offers for a specific hotel
            response = self.amadeus.shopping.hotel_offers_search.get(
                hotelIds=hotelIds, adults=adults, checkInDate=check_in_date, checkOutDate=check_out_date)
            
            return parse_hotel(response.data[:3]) 
        except ResponseError as error:
            return f"An error occurred: {error}"
