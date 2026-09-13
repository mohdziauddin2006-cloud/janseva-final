import os, sys, time, subprocess

def start_bot(): return subprocess.Popen([sys.executable, "bot.py"])
def start_web(): 
    port = os.getenv("PORT", "8501")
    return subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", port, "--server.address", "0.0.0.0", "--server.headless", "true"])

if __name__ == "__main__":
    b_proc, w_proc = start_bot(), start_web()
    while True:
        if b_proc.poll() is not None: b_proc = start_bot()
        if w_proc.poll() is not None: w_proc = start_web()
        time.sleep(10)