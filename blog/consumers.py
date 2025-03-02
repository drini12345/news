import json
import asyncio
import requests
from datetime import datetime, timedelta
import pytz
from channels.generic.websocket import AsyncWebsocketConsumer
from football.api import football_api

API_URL = 'http://api.football-data.org/v4/matches'  # Replace with your API
HEADERS = {"X-Auth-Token": football_api}  # Replace with your API key

class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.match_task = asyncio.create_task(self.send_match_updates())

    async def disconnect(self, close_code):
        if self.match_task:
            self.match_task.cancel()

    async def send_match_updates(self):
        """Fetch live match data and send updates to the frontend every 30 seconds."""
        while True:
            matches = await self.get_live_matches()
            print("Sending matches:", matches)  # Add logging here
            await self.send(json.dumps({"matches": matches}))
            await asyncio.sleep(10)  # Update every 10 seconds

    async def get_live_matches(self):
        response = requests.get(API_URL, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            matches = []
            for match in data.get("matches", []):
                home_team = match.get("homeTeam", {}).get("name", "N/A")
                away_team = match.get("awayTeam", {}).get("name", "N/A")
                match_time = self.calculate_match_time(match.get("utcDate", ""), match.get("status", ""))

                # Extract scores (handle missing values)
                home_score = match.get("score", {}).get("fullTime", {}).get("home", 0)
                away_score = match.get("score", {}).get("fullTime", {}).get("away", 0)

                matches.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "match_time": match_time,
                    "home_score": home_score if home_score is not None else 0,
                    "away_score": away_score if away_score is not None else 0,
                })

            return matches
        return []

    def calculate_match_time(self, start_time, status):
        """Ensure correct match time, including half-time pause and second-half restart from 45:00."""
        now = datetime.now(pytz.UTC)
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            return "Invalid Time"  # Handle incorrect date formats safely

        # Match not started yet
        if status in ["TIMED", "SCHEDULED"]:
            return "Not Started"

        # Stop counting at half-time
        if status == "HALF_TIME":
            return "45:00 (HT)"

        # Match paused (e.g., delayed, weather issues)
        if status == "PAUSED":
            return "HT"

        # Match finished
        if status == "FINISHED":
            return "FULL TIME"

        if status == "SUSPENDED":
            return "Suspended"

        # Calculate elapsed time in minutes
        elapsed = (now - start_dt).total_seconds() // 60

        if elapsed < 0:
            return "Not Started"  # Prevent negative values

        # First half (0-45 min)
        if elapsed < 45:
            return f"{int(elapsed)}:00"

        # **Ensure half-time pause**
        half_time_duration = 15  # Standard half-time duration (adjust if needed)
        second_half_start_time = start_dt + timedelta(minutes=45 + half_time_duration)

        # **If still in half-time, don't count further**
        if now < second_half_start_time:
            return "45:00 +"  # Ensures the clock doesn't count up during half-time

        # **Second half (45-90 min)**
        second_half_minutes = (now - second_half_start_time).total_seconds() // 60

        # Ensure second-half starts exactly from 45:00
        return f"{45 + int(second_half_minutes)}:00" if second_half_minutes < 45 else "90:00+"


