import os
import windfinder

from facebook import GraphAPI
from dotenv import load_dotenv

load_dotenv()
facebookAccessToken = os.getenv("facebookAccessToken")
pageID = os.getenv("pageID")

location = "weston_southampton"

forecast = windfinder.produceForecastText(location)

message = "Yooo, here is the forecast for the following week and when you could take the boats out, please let me know if you plan on taking them out!\n\n" + forecast + "\n\nThis data is produced by a computer so please check the forecasts and tides before you go at sailing just to confirm!"
link = "https://www.windfinder.com/forecast/weston_southampton"

graph = GraphAPI(access_token=facebookAccessToken)

graph.put_object(pageID, "feed", message=message, link=link)
print(graph.get_connections(pageID, "feed"))