import xml.etree.ElementTree as ET
import re
import urllib.parse
import argparse
import os
from datetime import timedelta

def format_time(seconds, full_format=True):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    millis = int(round((td.total_seconds() - total_seconds) * 1000))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if full_format:
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"
    else:
        return f"{hours:02}:{minutes:02}:{secs:02}"

def decode_xspf_path(location_text: str) -> str:
    """
    Decode file:///… URI from XSPF to a local filesystem path on this OS.
    """
    # Strip leading scheme
    path = location_text
    if path.lower().startswith("file:///"):
        path = path[8:]  # keep the third slash as part of path
    # URL-decode
    path = urllib.parse.unquote(path)
    # Normalize slashes for current OS
    path = path.replace("/", os.sep)
    return path

def extract_bookmark_times(vlc_option_text: str) -> list[float]:
    """
    VLC stores bookmarks like:
      bookmarks={name=...,time=57.273},{name=...,time=62.473},...
    We return the list of times as floats, preserving order.
    """
    return [float(t) for t in re.findall(r'time=([\d.]+)', vlc_option_text)]

def main():
    parser = argparse.ArgumentParser(description="Prepare ffmpeg cuts from VLC .xspf bookmarks (all tracks).")
    parser.add_argument('-i', '--input', required=True, help="Path to XSPF file exported from VLC")
    parser.add_argument('-t', '--target', default=os.getcwd(), help="Target output directory for cuts.txt and clips")
    args = parser.parse_args()

    os.makedirs(args.target, exist_ok=True)

    ns = {
        'xspf': 'http://xspf.org/ns/0/',
        'vlc': 'http://www.videolan.org/vlc/playlist/ns/0/'
    }

    tree = ET.parse(args.input)
    root = tree.getroot()
    tracks = root.findall(".//xspf:trackList/xspf:track", ns)

    cuts_path = os.path.join(args.target, "cuts.txt")
    wrote_any = False

    with open(cuts_path, "w", encoding="utf-8") as f:
        for track_idx, track in enumerate(tracks):
            # Find a <vlc:option> that contains bookmarks=
            option_els = track.findall("xspf:extension/vlc:option", ns)
            option_el = next((el for el in option_els if el.text and 'bookmarks=' in el.text), None)
            if option_el is None:
                continue  # no bookmarks on this track

            location_el = track.find("xspf:location", ns)
            if location_el is None or not location_el.text:
                # Skip malformed track (no location)
                continue

            full_path = decode_xspf_path(location_el.text)
            if not full_path:
                continue

            bookmarks = extract_bookmark_times(option_el.text)
            if not bookmarks:
                continue

            # Sort just in case VLC wrote them out of order (usually already ordered)
            bookmarks = sorted(bookmarks)

            # If odd number of times, ignore the last dangling start
            if len(bookmarks) % 2 != 0:
                bookmarks = bookmarks[:-1]

            stem = os.path.splitext(os.path.basename(full_path))[0]

            clip_num = 1
            for i in range(0, len(bookmarks), 2):
                start_t = bookmarks[i]
                end_t = bookmarks[i + 1]

                # Safety: ensure end >= start; if not, skip this pair
                if end_t < start_t:
                    continue

                # 5-second preroll logic
                ss_cut = max(0.0, start_t - 5.0)

                # Unique temp clip per source/clip to avoid overwrite
                temp_clip = os.path.join(args.target, f"{stem}-temp-{clip_num:03d}.mp4")
                final_clip = os.path.join(args.target, f"{stem}_clip{clip_num:03d}.mp4")

                # Build first pass: copy stream into temp segment
                # We keep your original behavior: -ss as output option (after -i) and -to as absolute timestamp.
                # This means -to is relative to the original input timeline.
                f.write('ffmpeg -i "{}"'.format(full_path))
                if ss_cut > 0:
                    f.write(' -ss {}'.format(format_time(ss_cut)))
                f.write(' -to {} -c copy -y "{}"\n'.format(format_time(end_t), temp_clip))

                # Second pass: trim exact start within the temp segment
                if ss_cut == 0:
                    # No preroll in temp, so seek to the real start time inside temp
                    f.write('ffmpeg -i "{}" -ss {} -vcodec h264 -acodec aac "{}"\n'
                            .format(temp_clip, format_time(start_t), final_clip))
                else:
                    # Temp already begins 5s before the real start; now remove those 5s
                    f.write('ffmpeg -i "{}" -ss 00:00:05 -vcodec h264 -acodec aac "{}"\n'
                            .format(temp_clip, final_clip))

                clip_num += 1

            wrote_any = True

    if not wrote_any:
        raise ValueError("No tracks with bookmarks were found in the XSPF.")

    print(f"Written ffmpeg commands to: {cuts_path}")

if __name__ == "__main__":
    main()
