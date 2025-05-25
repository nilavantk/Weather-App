import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import requests, json, os, datetime, logging
from collections import defaultdict, Counter

# ---------------------- Account Management ----------------------

USER_FILE = "users.json"
LOG_FILE = "weather_app.log"
OUTPUT_FILE = "weather_report.txt"
API = "cfc4cabd03006b7c75ede933b9154512"

URLS = {
    "geo": "https://api.openweathermap.org/geo/1.0/direct",
    "current": "https://api.openweathermap.org/data/2.5/weather",
    "forecast": "https://api.openweathermap.org/data/2.5/forecast",
    "meteo": "https://api.open-meteo.com/v1/forecast"
}

logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, 'w') as f:
            json.dump({}, f)
    with open(USER_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

def register():
    users = load_users()
    username = simpledialog.askstring("Register", "Enter new username:")
    if not username:
        return
    if username in users:
        messagebox.showerror("Error", "Username already exists.")
        return
    password = simpledialog.askstring("Register", "Enter password:", show='*')
    if not password:
        return
    users[username] = password
    save_users(users)
    messagebox.showinfo("Success", "Account created successfully!")

def login():
    users = load_users()
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    if username in users and users[username] == password:
        messagebox.showinfo("Success", f"Welcome, {username}!")
        login_window.destroy()
        open_weather_app(username)
    else:
        messagebox.showerror("Login Failed", "Invalid username or password.")

# ---------------------- Weather Application ----------------------

def fetch(url, params):
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logging.error(f"Error fetching from {url}: {e}")
        return None

def get_latlon(city):
    data = fetch(URLS["geo"], {"q": city, "appid": API, "limit": 1})
    return (data[0]["lat"], data[0]["lon"]) if data else (None, None)

def current_weather(city):
    d = fetch(URLS["current"], {"q": city, "appid": API, "units": "metric"})
    if d:
        return f"Weather: {d['weather'][0]['description'].capitalize()}\nTemperature: {d['main']['temp']}°C\nHumidity: {d['main']['humidity']}%\nWind Speed: {d['wind']['speed']} m/s"
    return "Unable to fetch current weather."

def past_weather(lat, lon):
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=3)).isoformat()
    end = (today - datetime.timedelta(days=1)).isoformat()
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": ["temperature_2m_max", "temperature_2m_min", "windspeed_10m_max"],
        "timezone": "auto"
    }
    d = fetch(URLS["meteo"], params)
    if d:
        return [
            f"{d['daily']['time'][i]}: Avg Temp: {round((d['daily']['temperature_2m_max'][i] + d['daily']['temperature_2m_min'][i])/2, 1)}°C, Max Wind: {d['daily']['windspeed_10m_max'][i]} m/s"
            for i in range(3)
        ]
    return ["No past weather data."]

def forecast(city):
    d = fetch(URLS["forecast"], {"q": city, "appid": API, "units": "metric"})
    if not d:
        return ["No forecast data."]
    
    days = defaultdict(list)
    for entry in d["list"]:
        date = entry["dt_txt"].split()[0]
        days[date].append(entry)

    today = datetime.date.today()
    output = []

    for i in range(1, 4):
        day = (today + datetime.timedelta(days=i)).isoformat()
        if day in days:
            group = days[day]
            desc = Counter(x["weather"][0]["description"].capitalize() for x in group).most_common(1)[0][0]
            temp = round(sum(x["main"]["temp"] for x in group) / len(group), 1)
            hum = round(sum(x["main"]["humidity"] for x in group) / len(group), 1)
            wind = round(sum(x["wind"]["speed"] for x in group) / len(group), 1)
            output.append(f"{day}: {desc}, {temp}°C, {hum}% humidity, {wind} m/s wind")
    return output

def show_weather(city):
    lat, lon = get_latlon(city)
    if lat is None:
        return "City not found."

    report = f"\nWeather Report for {city.title()}\n" + "-"*40 + "\n"
    report += "\n--- Current Weather ---\n" + current_weather(city) + "\n"
    report += "\n--- Past 3 Days ---\n" + "\n".join(past_weather(lat, lon)) + "\n"
    report += "\n--- Next 3 Days Forecast ---\n" + "\n".join(forecast(city)) + "\n"

    with open(OUTPUT_FILE, "a") as f:
        f.write(report + "\n")

    logging.info(f"Weather report generated for {city}")
    return report

def open_weather_app(username):
    root = tk.Tk()
    root.title(f"🌤️ Weather Forecast Application - Logged in as {username}")
    root.geometry("600x600")
    root.resizable(False, False)

    def get_weather():
        city = city_entry.get().strip()
        if not city:
            messagebox.showwarning("Missing Input", "Please enter a city name.")
            return

        output_box.config(state='normal')
        output_box.delete(1.0, tk.END)
        result = show_weather(city)
        output_box.insert(tk.END, result)
        output_box.config(state='disabled')

    def view_log():
        if not os.path.exists(OUTPUT_FILE):
            messagebox.showinfo("No Logs", "No weather logs found.")
            return

        with open(OUTPUT_FILE, "r") as f:
            content = f.read()

        log_window = tk.Toplevel(root)
        log_window.title("Saved Weather Logs")
        log_box = scrolledtext.ScrolledText(log_window, wrap='word', width=80, height=25)
        log_box.pack(padx=10, pady=10)
        log_box.insert(tk.END, content)
        log_box.config(state='disabled')

    tk.Label(root, text="Weather Forecast", font=("Helvetica", 18, "bold")).pack(pady=10)

    frame = tk.Frame(root)
    frame.pack(pady=5)
    tk.Label(frame, text="Enter City Name:", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=5)
    city_entry = tk.Entry(frame, font=("Helvetica", 12), width=30)
    city_entry.pack(side=tk.LEFT)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Get Weather", command=get_weather, width=15).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="View Log", command=view_log, width=15).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="Exit", command=root.destroy, width=10).pack(side=tk.LEFT, padx=10)

    output_box = scrolledtext.ScrolledText(root, width=70, height=25, wrap='word', font=("Courier", 10))
    output_box.pack(pady=10)
    output_box.config(state='disabled')

    root.mainloop()

# ---------------------- Login GUI ----------------------

login_window = tk.Tk()
login_window.title("User Login")
login_window.geometry("350x200")
login_window.resizable(False, False)

tk.Label(login_window, text="Login to Weather App", font=("Helvetica", 16)).pack(pady=10)

tk.Label(login_window, text="Username:").pack()
username_entry = tk.Entry(login_window)
username_entry.pack()

tk.Label(login_window, text="Password:").pack()
password_entry = tk.Entry(login_window, show="*")
password_entry.pack()

tk.Button(login_window, text="Login", command=login, width=12).pack(pady=5)
tk.Button(login_window, text="Register", command=register, width=12).pack()

login_window.mainloop()

