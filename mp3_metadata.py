import sys, json, argparse
import mutagen.id3 as id3

# -------------------------------------------------------------------------------------------------------------------- #
#                                                 set global variables                                                 #
# -------------------------------------------------------------------------------------------------------------------- #
default_encoding = 3
frames = {"TIT2": "Title/songname/content description",
		  "TALB": "Album/Movie/Show title",
		  "TPE1": "Lead performer(s)/Soloist(s)",
		  "TPE2": "Band/orchestra/accompaniment",
		  "COMM": "Comments",
		  "CTOC": "",
		  "TCOM": "Composer",
		  "TCON": "Content type",
		  "TDRC": "Recording time",
		  "TRCK": "Track number/Position in set"
}

time_conversion_factors = [1, 1000, 60, 60, 24]
for i in range(1, len(time_conversion_factors)):
	time_conversion_factors[i] *= time_conversion_factors[i - 1]

console_description = "This is a program to tag a MP3 file using mutagen for Python.\nDocumentation for mutagen.id3 is available under https://mutagen.readthedocs.io/en/latest/api/id3.html\nand this code is available under https://github.com/jonaheinke/mp3_metadata"
console_epilog = "allowed frames:\n  see https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames for a complete list\n\nCopyright (c) 2021 Jona Heinke under MIT license"
parser = argparse.ArgumentParser(description = console_description, epilog = console_epilog, formatter_class = argparse.RawTextHelpFormatter)
parser.add_argument("mp3file", metavar = "<path-to-mp3>", type = str, help = "")
parser.add_argument("jsonfile", metavar = "<path-to-json>", type = str, help = "")
parser.add_argument("-n", action = "store_true", help = "do not overwrite an existing file")
args = parser.parse_args()



# -------------------------------------------------------------------------------------------------------------------- #
#                                                    misc functions                                                    #
# -------------------------------------------------------------------------------------------------------------------- #
def print_help():
	print("Frames:")
	map(lambda frame: print(frame[0] + ": " + frame[1]), frames.items())
	print("There are many more frames I can write. See https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames for a complete list.")
	exit()

def convert_to_ms(duration):
	return sum(int(amount) * factor for amount, factor in zip(duration.split(":")[::-1], time_conversion_factors))

def instantiate_tag(tag, value):
	tag_class = getattr(id3, tag)
	parent_class = tag_class.__bases__[0]
	if parent_class in (id3.TextFrame, id3.NumericTextFrame, id3.NumericPartTextFrame, id3.TimeStampTextFrame):
		return tag_class(encoding = default_encoding, text = value)
	if parent_class in (id3.UrlFrame, id3.UrlFrameU):
		if tag == "WXXX":
			return tag_class(encoding = default_encoding, url = value)
		else:
			return tag_class(value)
	if parent_class in (id3.TIPL, id3.PairedTextFrame):
		return tag_class(encoding = default_encoding, people = value)
	else:
		print("Tag #### can't be set. Please use a dict to describe what data you want.")
		return None



# -------------------------------------------------------------------------------------------------------------------- #
#                                                      read files                                                      #
# -------------------------------------------------------------------------------------------------------------------- #
if len(sys.argv) < 3:
	print("Too few arguments.")
	print_help()
elif not sys.argv[1].endswith(".mp3"):
	print("Wrong filetype for MP3 file.")
	print_help()
elif not sys.argv[2].endswith(".json"):
	print("Wrong filetype for json file.")
	print_help()

#read mp3
tags = id3.ID3()
try:
	tags.load(sys.argv[1], translate = True, v2_version = 3)
	tags.delete()
except id3.ID3NoHeaderError:
	tags = id3.ID3()
except Exception as e:
	print("MP3-Input failed")
	print(e)
	exit()

#read json
try:
	with open(sys.argv[2], encoding = "utf-8-sig") as f:
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



# -------------------------------------------------------------------------------------------------------------------- #
#                                                      processing                                                      #
# -------------------------------------------------------------------------------------------------------------------- #
for tag, value in target.items():
	if tag in frames:#.keys()
		if tag == "CTOC": #https://id3.org/id3v2-chapters-1.0
			i = 0
			child_element_ids = []
			for chap in value:
				if "sub_frames" in chap:
					for sub_frame_key, sub_frame_value in chap["sub_frames"].items():
						chap["sub_frames"][sub_frame_key] = instantiate_tag(sub_frame_key, sub_frame_value) #{k: instantiate_tag(k, v) for k, v in chap["sub_frames"]}
				child_element_ids.append(f"ch{i}")
				tags.add(id3.CHAP(f"ch{i}", start_time = 0, end_time = 0, sub_frames = []))
				i += 1
			tags.add(id3.CTOC("toc", id3.CTOCFlags.TOP_LEVEL | id3.CTOCFlags.ORDERED, child_element_ids))
		else:
			if isinstance(value, str):
				tags.add(instantiate_tag(tag, value))
			elif isinstance(value, dict):
				if "encoding" not in value:
					value["encoding"] = default_encoding
				tags.add(getattr(id3, tag)(**value))
	else:
		print(f"Tag {tag} not recognized.")

#audio["TIT2"] = getattr(mutagen.id3, "TIT2")(encoding = 3, text = "nice")
#print(locals()["TALB"](encoding = 3, text = "nice"))
#audio["TIT2"] = newframe("TIT2")(encoding = 3, text = "nice")
#audio["TIT2"] = TIT2(encoding = 3, text = "nice")
#from mutagen.id3 import TIT2
#print(TIT2)
#audio["TIT2"] = newframe("TIT2")(encoding = 3, text = "nice")
#audio["TIT2"] = getattr(sys.modules[__name__], "TIT2")(encoding = 3, text = "nice")



# -------------------------------------------------------------------------------------------------------------------- #
#                                                        saving                                                        #
# -------------------------------------------------------------------------------------------------------------------- #
tags.save(sys.argv[1], v2_version = 3, padding = lambda info: max(info.padding, 0))