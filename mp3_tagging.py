import sys, json, argparse
import mutagen.id3 as id3

# -------------------------------------------------------------------------------------------------------------------- #
#                                                 set global variables                                                 #
# -------------------------------------------------------------------------------------------------------------------- #
frames = {"TIT2": "Title/songname/content description", #https://id3.org/id3v2.4.0-frames
		  "TALB": "Album/Movie/Show title",
		  "TPE1": "Lead performer(s)/Soloist(s)",
		  "CTOC": "",
		  "TCOM": "Composer",
		  "TCON": "Content type",
		  "TCOP": "Copyright message",
		  "TBPM": "BPM (beats per minute)",
		  "TDRC": "Recording time"
}

default_encoding = 3 #TODO: add command line option to change this

time_conversion_factors = [1, 1000, 60, 60, 24]
for i in range(1, len(time_conversion_factors)):
	time_conversion_factors[i] *= time_conversion_factors[i - 1]

console_description = "This is a program to tag a MP3 file using mutagen for Python.\nDocumentation for mutagen.id3 is available under https://mutagen.readthedocs.io/en/latest/api/id3.html\nand this code is available under https://github.com/jonaheinke/mp3_metadata"
console_epilog = "allowed frames:\n  see https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames for a complete list\n\nCopyright (c) 2021 Jona Heinke under MIT license"
#map(lambda frame: print(frame[0] + ": " + frame[1]), frames.items())
parser = argparse.ArgumentParser(description = console_description, epilog = console_epilog, formatter_class = argparse.RawTextHelpFormatter)
parser.add_argument("mp3file", metavar = "<path-to-mp3>", type = str, help = "")
parser.add_argument("jsonfile", metavar = "<path-to-json>", type = str, help = "")
parser.add_argument("-n", action = "store_true", help = "do not overwrite an existing file") #TODO: change command line option to a more common/fitting one
args = parser.parse_args()



# -------------------------------------------------------------------------------------------------------------------- #
#                                                    misc functions                                                    #
# -------------------------------------------------------------------------------------------------------------------- #
def convert_to_ms(timestamp):
	if isinstance(timestamp, int):
		return abs(timestamp)
	elif isinstance(timestamp, str):
		""" TODO: maybe implement this
		import re
		result = re.sub("[^0-9:]", "", timestamp)
		"""
		return sum(int(amount) * factor for amount, factor in zip(timestamp.split(":")[::-1], time_conversion_factors))
	else:
		print(f"The timestamp of type {type(timestamp)} wasn't recognized. Please use a str or int to describe the timestamp.")
		print("format: [[[[%d:]%h:]%m:]%s:]%ms | int in ms")
		return 0

def instantiate_tag(tag, value): #TODO: look into lists of artists -> need for isinstance(value, list?) #TODO: allow paths to pictures
	tag_class = getattr(id3, tag)
	parent_class = tag_class.__bases__[0]
	if isinstance(value, str):
		if parent_class in (id3.TextFrame, id3.NumericTextFrame, id3.NumericPartTextFrame, id3.TimeStampTextFrame):
			return tag_class(encoding = default_encoding, text = value)
		elif parent_class in (id3.UrlFrame, id3.UrlFrameU):
			if tag == "WXXX":
				return tag_class(encoding = default_encoding, url = value)
			else:
				return tag_class(value)
		elif parent_class in (id3.TIPL, id3.PairedTextFrame):
			return tag_class(encoding = default_encoding, people = value)
		else:
			print(f"Tag {tag} can't be set. Please use a dict to describe what data you want to set.")
			return None
	elif isinstance(value, dict):
		if "encoding" not in value:
			value["encoding"] = default_encoding
		return tag_class(**value)
	else:
		print(f"{tag}'s value of type {type(value)} can't be set. Please use a str or dict to describe what data you want to set.")
		return None



# -------------------------------------------------------------------------------------------------------------------- #
#                                                      read files                                                      #
# -------------------------------------------------------------------------------------------------------------------- #
if not args["mp3file"].endswith(".mp3"):
	print("Wrong filetype for MP3 file.")
	exit()
elif not args["jsonfile"].endswith(".json"):
	print("Wrong filetype for JSON file.")
	exit()

#read mp3
tags = id3.ID3()
try:
	tags.load(args["mp3file"], translate = True, v2_version = 3)
	tags.delete()
except id3.ID3NoHeaderError:
	tags = id3.ID3()
except FileNotFoundError:
	print("MP3 file couldn't be found.")
	exit()
except PermissionError:
	print("MP3 file couldn't be read. Permission denied.")
	exit()
except Exception as e:
	print("Unknown error occured while reading MP3 file.")
	print(e)
	exit()

#read json
try:
	with open(args["jsonfile"], encoding = "utf-8-sig") as f:
		try:
			target = json.load(f)
		except json.decoder.JSONDecodeError:
			print("JSON file couldn't be decoded.")
			exit()
except FileNotFoundError:
	print("JSON file couldn't be found.")
	exit()
except PermissionError:
	print("JSON file couldn't be read. Permission denied.")
	exit()
except Exception as e:
	print("Unknown error occured while reading JSON file.")
	print(e)
	exit()



# -------------------------------------------------------------------------------------------------------------------- #
#                                                      processing                                                      #
# -------------------------------------------------------------------------------------------------------------------- #
for tag, value in target.items():
	if tag == "CTOC": #standardised chapter format: https://id3.org/id3v2-chapters-1.0
		i = 0
		child_element_ids = []
		for chap in value:
			if "sub_frames" in chap:
				temp_sub_frames = []
				for sub_frame_information in chap["sub_frames"].items():
					temp_sub_frames.append(instantiate_tag(*sub_frame_information))
			child_element_ids.append(f"ch{i}")
			tags.add(id3.CHAP(f"ch{i}", start_time = convert_to_ms(chap["start"]), end_time = convert_to_ms(chap["end"]), sub_frames = temp_sub_frames))
			i += 1
		tags.add(id3.CTOC("toc", id3.CTOCFlags.TOP_LEVEL | id3.CTOCFlags.ORDERED, child_element_ids))
	else:
		tags.add(instantiate_tag(tag, value))



# -------------------------------------------------------------------------------------------------------------------- #
#                                                        saving                                                        #
# -------------------------------------------------------------------------------------------------------------------- #
if args["n"]: #TODO: copy mp3 file as well
	save_path = args["mp3file"].replace(".mp3", "_tagged.mp3")
else:
	save_path = args["mp3file"]
tags.save(save_path, v2_version = 3, padding = lambda info: max(info.padding, 0))