import xml.etree.ElementTree as ET
import re
import urllib.parse
import argparse
import os
from datetime import timedelta

def format_time(seconds, full_format=True):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    millis = int((td.total_seconds() - total_seconds) * 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if full_format:
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"
    else:
        return f"{hours:02}:{minutes:02}:{secs:02}"

def main():
    parser = argparse.ArgumentParser(description="Prepare ffmpeg cuts from VLC .xspf bookmarks.")
    parser.add_argument('-i', '--input', required=True, help="Path to XSPF file exported from VLC")
    parser.add_argument('-t', '--target', default=os.getcwd(), help="Target output directory")
    args = parser.parse_args()

    ns = {
        'xspf': 'http://xspf.org/ns/0/',
        'vlc': 'http://www.videolan.org/vlc/playlist/ns/0/'
    }

    tree = ET.parse(args.input)
    root = tree.getroot()

    location_el = root.find(".//xspf:location", ns)
    if location_el is None:
        raise ValueError("No <location> tag found in the XML.")
    location = urllib.parse.unquote(location_el.text.replace("file:///", "").replace("/", os.sep))
    full_path = location
    base_filename = os.path.basename(full_path)

    option_el = root.find(".//vlc:option", ns)
    if option_el is None:
        raise ValueError("No <vlc:option> tag found in the XML.")
    bookmarks_raw = option_el.text
    bookmarks = re.findall(r'time=([\d.]+)', bookmarks_raw)
    bookmarks = list(map(float, bookmarks))

    cuts_path = os.path.join(args.target, "cuts.txt")
    with open(cuts_path, "w", encoding="utf-8") as f:
        for i in range(0, len(bookmarks), 2):
            original_start = bookmarks[i]
            ss_cut = max(0, original_start - 5)
            temp_clip = os.path.join(args.target, "temp-clip.mp4")
            final_clip = os.path.join(args.target, f"clip{(i // 2) + 1:03d}.mp4")

            ss_cut_str = format_time(ss_cut)
            f.write(f'ffmpeg -i "{full_path}"')
            if ss_cut > 0:
                f.write(f' -ss {ss_cut_str}')
            f.write(f' -to {format_time(bookmarks[i + 1]) if i + 1 < len(bookmarks) else ""} -c copy -y "{temp_clip}"\n')

            if ss_cut == 0:
                f.write(f'ffmpeg -i "{temp_clip}" -ss {format_time(original_start)} -vcodec h264 -acodec aac "{final_clip}"\n')
            else:
                f.write(f'ffmpeg -i "{temp_clip}" -ss 00:00:05 -vcodec h264 -acodec aac "{final_clip}"\n')

if __name__ == "__main__":
    main()
