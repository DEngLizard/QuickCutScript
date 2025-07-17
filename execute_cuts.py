import subprocess

def run_ffmpeg_commands(file_path="cuts.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        commands = f.read().splitlines()

    for i, cmd in enumerate(commands, 1):
        print(f"Executing command {i}/{len(commands)}...")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"Command failed: {cmd}")
            break
    print("Done.")

if __name__ == "__main__":
    run_ffmpeg_commands()