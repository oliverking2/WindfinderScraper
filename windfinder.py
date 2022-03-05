import requests
from bs4 import BeautifulSoup
import datetime

"""
TO DO LIST
- Telegram notifications on a Monday, forecast + tide times
- take into account pressure effect on tides
- create graphs of wind
- account for sunrise/sunset
- careful in larger tides, e.g. 4.8 at 11:50, sail till 14:20?
"""


def getData(container, classname):
    return [value.get_text().strip().strip("\nm") for value in container.find_all(class_=classname)]


def getWindVals(container):
    windData = container.find_all(class_="cell-wind-3 weathertable__cellgroup")
    windBase = []
    windGust = []

    for hour in windData:
        base, gust = [value.get_text() for value in hour.find_all(class_="units-ws")]
        windBase.append(base)
        windGust.append(gust)
    return windBase, windGust


def getTideTimes(container):
    tideData = container.find_all(class_="cell-tides weathertable__cellgroup weathertable__cellgroup--stacked two")
    tideTime = []
    tideLowHigh = []

    for hour in tideData:
        tideTime.append(
            hour.find_all(class_="data-tidefreq data--minor weathertable__cell data-time")[0].get_text().strip())
        tideLowHigh.append(hour.find_all(class_="data-tidedirection__symbol")[0]['class'][1].split("-")[-1])
    return tideTime, tideLowHigh


def indexFromTime(time):
    if time > datetime.datetime(1900, 1, 2):
        time = datetime.datetime(1900, 1, 1, 23, 59).time()
    elif time < datetime.datetime(1900, 1, 1):
        time = datetime.datetime(1900, 1, 1, 0, 0).time()
    else:
        time = time.time()

    timeArray = str(time).split(":")[:2]
    hours = int(timeArray[0]) + int(timeArray[1])/60

    return round(hours/3)


def analyseWind(base, gust):
    base = list(map(int, base))
    gust = list(map(int, gust))

    baseChange = "constant"
    gustChange = "constant"
    baseDelta = base[1] - base[0]
    gustDelta = gust[1] - gust[0]

    if baseDelta > 1:
        baseChange = "increasing"
    elif baseDelta < -1:
        baseChange = "decreasing"
    if gustDelta > 1:
        gustChange = "increasing"
    elif gustDelta < -1:
        gustChange = "decreasing"

    if len(base) > 2:
        baseDelta2 = base[2] - base[1]
        gustDelta2 = gust[2] - gust[1]

        if baseDelta >= 0 and baseDelta2 >= 1:
            baseChange = "increasing"
        elif baseDelta <= 0 and baseDelta2 <= -1:
            baseChange = "decreasing"
        elif baseDelta > 1 and baseDelta2 < -1:
            baseChange = "increase decrease"
        elif baseDelta < -1 and baseDelta2 > 1:
            baseChange = "decrease increase"
        if gustDelta >= 0 and gustDelta2 >= 1:
            gustChange = "increasing"
        elif gustDelta <= 0 and gustDelta2 <= -1:
            gustChange = "decreasing"
        elif gustDelta > 1 and gustDelta2 < -1:
            gustChange = "increase decrease"
        elif gustDelta < -1 and gustDelta2 > 1:
            gustChange = "decrease increase"

    baseLow, baseHigh = min(base), max(base)
    gustLow, gustHigh = min(gust), max(gust)
    average = sum(base) / len(base)

    return baseChange, gustChange, baseLow, baseHigh, gustLow, gustHigh, average

def getForecast(location):
    forecast = {}
    page = requests.get("https://www.windfinder.com/forecast/" + location) # weston_southampton
    # page = requests.get("https://www.windfinder.com/forecast/mount_batten_plymouth")
    soup = BeautifulSoup(page.content, 'html.parser')

    for a in range(1, 11):  # iterate over each days forecast
        forecastContainer = soup.find_all(
            class_="weathertable forecast-day forecast forecast-day-8 fc-day-index-" + str(a))
        if forecastContainer == []:
            forecastContainer = soup.find_all(
                class_="weathertable forecast-day forecast forecast-day-7 fc-day-index-" + str(a))
        for dailyForecast in forecastContainer:
            date = getData(dailyForecast, "h h--4 weathertable__headline")[0]
            direction = getData(dailyForecast,
                                "data-direction-unit units-wd units-wd-deg data--minor weathertable__cell")

            windBaseValues, windGustValues = getWindVals(dailyForecast)

            tideHeight = getData(dailyForecast, "data-tideheight data--minor weathertable__cell")
            tideTimes, tideHighLow = getTideTimes(dailyForecast)

            forecast[date] = {"direction": direction, "base": windBaseValues, "gust": windGustValues,
                              "tideheight": tideHeight, "tidetimes": [tideTimes, tideHighLow]}
    return forecast

def analyseForecast(forecast):
    analysedForecast = []
    for day in forecast:
        tideTimes, tideType = forecast[day]["tidetimes"]
        for indexTide, tideTime in enumerate(tideTimes):
            if tideType[indexTide] == "high":
                time = datetime.datetime.strptime(tideTime, "%H:%M")
                tideTimeText = " ".join(["High Tide is at:", tideTime])

                timeEarly = time - datetime.timedelta(hours=2.5)
                if timeEarly < datetime.datetime(1900, 1, 1):
                    timeEarly = datetime.datetime(1900, 1, 1, 0, 0)

                timeLate = time + datetime.timedelta(hours=2.5)
                if timeLate > datetime.datetime(1900, 1, 2):
                    timeLate = datetime.datetime(1900, 1, 1, 23, 59)

                if datetime.datetime(1, 1, 1, 9).time() < timeEarly.time() < datetime.datetime(1, 1, 1, 17).time() or datetime.datetime(1, 1, 1, 9).time() < timeLate.time() < datetime.datetime(1, 1, 1, 17).time():
                    if timeEarly.time() < datetime.datetime(1, 1, 1, 9).time():
                        timeEarly = datetime.datetime(1900, 1, 1, 9)

                    elif timeLate.time() > datetime.datetime(1, 1, 1, 17).time():
                        timeLate = datetime.datetime(1900, 1, 1, 17)

                    sessionLength = timeLate - timeEarly

                    if sessionLength > datetime.timedelta(hours=1.5):
                        earlyIndex = indexFromTime(timeEarly)
                        lateIndex = indexFromTime(timeLate) + 1
                        base, gust = forecast[day]["base"][earlyIndex:lateIndex], forecast[day]["gust"][earlyIndex:lateIndex]
                        baseChange, gustChange, baseLow, baseHigh, gustLow, gustHigh, average = analyseWind(base, gust)

                        date = "** " + " ".join([day, ":", timeEarly.strftime('%H:%M'), "-", timeLate.strftime('%H:%M')]) + " **"
                        sessionTime = str(sessionLength).split(":")[:2]
                        if sessionTime[1] == "00":
                            sessionDetails = " ".join(
                                ["Session Length:", sessionTime[0], "hours"])
                        else:
                            if sessionTime[0] == "1":
                                sessionDetails = " ".join(
                                    ["Session Length:", sessionTime[0], "hour", sessionTime[1], "minutes"])
                            else:
                                sessionDetails = " ".join(
                                    ["Session Length:", sessionTime[0], "hours", sessionTime[1], "minutes"])

                        if 6 < baseHigh < 22:
                            # print(baseChange, gustChange, baseLow, baseHigh, gustLow, gustHigh)
                            if baseChange == "increasing":
                                if gustChange == "increasing" or gustChange == "constant":
                                    forecastText = " ".join(list(map(str, ["Forecast:", baseLow, "gusting", gustLow,
                                                                           "increasing to", baseHigh, "gusting",
                                                                           gustHigh])))
                                else:
                                    forecastText = " ".join(list(map(str, ["Forecast: ", base[0], "gusting", gust[0],
                                                                           "changing to", base[len(base) - 1],
                                                                           "gusting", gust[len(base) - 1]])))
                            elif baseChange == "constant":
                                if gustChange == "increasing" or gustChange == "increase decrease":
                                    forecastText = " ".join(list(map(str, ["Forecast: ", baseLow, "gusting", gustLow,
                                                                           "increasing to", baseHigh, "gusting",
                                                                           gustHigh])))
                                elif gustChange == "constant":
                                    forecastText = " ".join(list(map(str, ["Forecast:", baseLow, "gusting", gustLow])))
                                elif gustChange == "decrease increase":
                                    forecastText = " ".join(list(map(str, ["Forecast: ", baseLow, "gusting", gustLow,
                                                                           "decreasing slightly then increasing to",
                                                                           baseHigh, "gusting", gustHigh])))
                                else:
                                    forecastText = " ".join(list(map(str, ["Forecast:", baseLow, "gusting", gustLow])))
                            elif baseChange == "decreasing":
                                if gustChange == "decreasing" or gustChange == "constant":
                                    forecastText = " ".join(list(map(str, ["Forecast:", baseHigh, "gusting", gustHigh,
                                                                           "decreasing to", baseLow, "gusting",
                                                                           gustLow])))
                                else:
                                    forecastText = " ".join(list(map(str, ["Forecast: ", base[0], "gusting", gust[0],
                                                                           "changing to", base[len(base) - 1],
                                                                           "gusting", gust[len(base) - 1]])))
                            elif baseChange == "increase decrease":
                                forecastText = " ".join(list(map(str, ["Forecast: ", baseLow, "gusting", gustLow,
                                                                       "increasing slightly to", baseHigh, "gusting",
                                                                       gustHigh, "and then decreasing again"])))
                            elif baseChange == "decrease increase":
                                forecastText = " ".join(list(map(str, ["Forecast: ", baseLow, "gusting", gustLow,
                                                                       "decreasing slightly then increasing to",
                                                                       baseHigh, "gusting", gustHigh])))
                            else:
                                print("Error: unknown weather data")
                        else:
                            print("Conditions not suitable")

                        analysedForecast.append([date, " \u2022  " + tideTimeText, " \u2022  " + sessionDetails, " \u2022  " + forecastText])
    return analysedForecast


def printForecast(forecast):
    for session in forecast:
        print("\n".join(session))
        print("\n")


def produceForecastText(location):
    forecast = getForecast(location)
    text = []

    for session in analyseForecast(forecast):
        text.append("\n".join(session))

    return "\n\n".join(text)

if __name__ == '__main__':
    forecast1 = getForecast("weston_southampton")
    data = analyseForecast(forecast1)
    printForecast(data)
