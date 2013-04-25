#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup, Comment
import json

# Global cache objects.
# This means we don't have to wait on web traffic.
_cached_json = None
_cached_bs_page = None
_cached_language = ""

class Hero(object):
    """ An object representing a hero. """
    def __init__(self, name, icon="", attr="", faction = "",
                 bio="", roles="", attack="",
                 key=""):
        self.name = name # Duh.
        self.icon = icon # A URL for the icon.
        self.attr = attr # Primary attribute.
        self.bio = bio # A biographical string.
        self.roles = roles # Roles that this hero can play.
        self.attack = attack # Attack type.
        self.faction = faction # Dire or Radiant.

        self.key = key # The name by which this hero is referred to in the JSON list.

    def __str__(self):
        return "{} ({})".format(self.name, self.key)

    def save_icon(self, path = None):
        """ Download the hero's icon and store it on disk. """
        if path == None:
            path = self.key + ".png"

        with open(path, "wb") as output:
            r = requests.get(self.icon)
            if r.status_code == 200:
                for chunk in r.iter_content():
                    output.write(chunk)

    def info(self):
        """ Return a string containing a summary of the hero. """
        return "{} - {fac}/{atr}/{atk} - {rls}"\
            .format(self.name,
                    fac=self.faction,
                    atr=self.attr,
                    rls=", ".join(self.roles),
                    atk=self.attack)

def get_languages():
    """ Return a list of acceptable languages.
    
    Returns a list of tuples: first is the human-readable name, second is the parameter Valve's webpage expects.
    Note that you need to have the webpage already, i.e. load it in English first.
    """
    page = get_web_page()
    lang_tags = page.find_all("a", "languageItem")
    return [(tag.string.lstrip().rstrip(), tag["href"][2:]) for tag in lang_tags]

def set_language(lang=""):
    """ Set the language to something other than English.
    
    Pass the second part of the language tuple to this function.
    This forces a cache reload for the BeautifulSoup page and the JSON list IFF the language is different.
    """
    global _cached_language, _cached_bs_page, _cached_json

    if _cached_language != lang:
        _cached_language = lang
        # Update the cached copy.
        get_web_page(lang=lang)
        get_json_list(lang=lang)

def get_web_page(url="http://www.dota2.com/heroes/", lang=""):
    """ Read the hero list from the official site, and return a BeautifulSoup object. """
    global _cached_language, _cached_bs_page

    if (lang != "" and _cached_language != lang) or _cached_bs_page is None:
        raw = requests.get(url + "?l=" + lang).text
        _cached_bs_page = BeautifulSoup(raw)

    return _cached_bs_page

def get_json_list(url="http://www.dota2.com/jsfeed/heropickerdata",
                  lang=""):
    """ Get a list of heroes in a nice JSON list.

    This is missing the hero icon, hero faction, and hero primary attribute. 
    """
    global _cached_json
    if (lang != "" and _cached_language != lang) or _cached_json is None:
        _cached_json = requests.get(url + "?l=" + lang).json() # Parse it using the Requests internal JSON thing.

    return _cached_json

def get_hero_info(heroName):
    """ Get the hero's icon, faction and attribute based on its name.

    Returns a tuple of (icon, attr, faction)
    icon is the URL for the icon.
    attr is the hero's primary attribute. ("Strength", "Intelligence", "Agility")
    faction is either "Dire" or "Radiant".
    """
    page = get_web_page()

    def matches_hero(tag):
        return tag.name == "a" \
            and "id" in tag.attrs\
            and heroName in tag["id"]

    # Get the tag object that holds this hero. We want to find out more information about them later.
    hero_tag = page.find_all(matches_hero)[0]
    img_src = hero_tag.img["src"]

    # What is their primary attribute?
    attribute = None
    if "heroColLeft" in hero_tag.parent.parent["class"]: # "class" is a list. This also will work for string comparisons, because yay Python.
        attribute = "Strength"
    elif "heroColMiddle" in hero_tag.parent.parent["class"]:
        attribute = "Agility"
    elif "heroColRight" in hero_tag.parent.parent["class"]:
        attribute = "Intelligence"

    # What faction are they part of?
    # Radiant are listed first, Dire second.
    # If we're in the first box, then that means we're Radiant.
    if hero_tag.parent.parent == page.find("div", hero_tag.parent.parent["class"]):
        faction = "Radiant"
    else:
        faction = "Dire"

    return (img_src, attribute, faction)

def get_all_heroes():
    """ Get a generator to iterate over all of the heroes on the page. """
    jsonObj = get_json_list()
    jsonKeys = jsonObj.keys()

    for key in jsonKeys:
        H = jsonObj[key]
        # Get the attribute and icon from the webpage.
        icon, attribute, faction = get_hero_info(key)

        yield Hero(H["name"], icon, attribute, faction,
                   H["bio"], H["roles_l"], H["atk_l"],
                   key)

def find_heroes(hlist, name="", attribute=None, role=None, attack=None):
    """ Find a list of hero objects with a particular property.
    
    Always returns a list.
    """
    def match_name(test):
        return name == "" or test.name == name or test.key == name
    def match_attr(test):
        return attribute is None or test.attr == attribute 
    def match_role(test):
        return role is None or frozenset(test.roles).issuperset(frozenset(role))
    def match_attack(test):
        return attack is None or test.attack == attack

    # Chain the filters to get the only matching list.
    found = list(filter(match_name, 
                        filter(match_attr,
                               filter(match_attack,
                                      filter(match_role, hlist)))))
    
    return found

def find_first_hero(hlist, *args):
    """ Find the first hero matching an expression, or None."""
    l = find_heroes(hlist, *args)
    if not l: return None
    return l[0]

def write_disk_cache(jspath="cached_list.json", webpath="cached_webpage.html"): 
    """ Save the cache to disk. Used in combination with read_disk_cache()"""
    with open(jspath, "w") as jsfile, open(webpath, "w") as webfile:
        JSON = get_json_list()
        BS_page = get_web_page()

        # Add a language comment to the page.
        BS_page.head.append(BeautifulSoup("<!--LANGUAGE=" + _cached_language + "-->"))

        jsfile.write(json.dumps(JSON))
        webfile.write(BS_page.prettify())

def read_disk_cache(jspath="cached_list.json", webpath="cached_webpage.html"):
    """ Load the webpage and stuff from disk. """
    global _cached_bs_page, _cached_json, _cached_language
    _cached_language = "" # We'll set this properly in a little bit.
    tmp_json = None
    tmp_page = None

    try:
        with open(jspath, "r") as jsfile, open(webpath, "r") as webfile:
            tmp_json = json.loads(jsfile.read()) # Load the json-formatted list.
            tmp_page = BeautifulSoup(webfile) # Aaand the webpage.

            _cached_json = tmp_json # By this point, any IOErrors will have already occurred.
            _cached_bs_page = tmp_page

            # What language is this?
            l = tmp_page.find(text=lambda t: isinstance(t, Comment) and t.string[:9] == "LANGUAGE=")
            _cached_language = l.string.split('=')[1]

    except IOError as e:
        # The file doesn't exist.
        # In this case, we have to load it from the web.
        # Leave the globals as we found them; i.e. just abort.
        print("Could not load from disk.")

### If we're run as a program, give the user a list of heroes. ###
if __name__ == "__main__":
    import sys

    if "-h" in sys.argv or "--help" in sys.argv:
        print("""Dota 2 Hero-pædia!
Options:
    -r    Read data from a cached copy of the webpage. This reduces network traffic.
    -w    Cache the webpage. Uses the current language. This creates two files: cached_list.json and cached_webpage.html.
    -L    List valid languages.
    -l    Specify the language you want to use. Can be combined with -w, but not with -r (idk why).
    -h    Show this help.
""")
        exit(0)

    if "-r" in sys.argv:
        read_disk_cache() # Read the disk cache. Only makes sense if we haven't just written it.

    if "-L" in sys.argv:
        print("Acceptable languages:")
        for human, param in get_languages():
            print("{}\t-\t{}".format(human, param))
        exit(0)

    if "-l" in sys.argv:
        set_language(sys.argv[sys.argv.index('-l') + 1])

    # Write the disk cache after the language is set.
    if "-w" in sys.argv:
        write_disk_cache()
        exit(0)

    heroes = list(get_all_heroes())

    print("Interactive hero browser!")
    print("Type 'exit' to exit.")
    line = ""

    try:
        while line not in ("exit", "quit"):
            line = input("> ")
            if line.split()[0] in ("help", "?", "HELP"):
                print("List of commands:")
                print("""  list\t:\tGives a list of all the heroes' names.
  bio\t:\tGives the bio for a particular hero.
  find\t:\tGives a list of heroes matching a set of criteria.
  info\t:\tGives a summary of a hero.
  
  Examples:
            find role=Carry,Durable attribute=Intelligence attack=Ranged
            bio Windrunner
            info naga_siren""")
                
            elif line.split()[0] in ("list", "LIST", "l"):
                for h in heroes: print(h)
            
            elif line.split()[0] in ("bio", "BIO", "b"):
                h = find_first_hero(heroes, " ".join(line.split()[1:]))

                # If we couldn't find anyone...
                if h is None:
                    print("Hero " + " ".join(line.split()[1:]) + " not found.")
                    continue
                else:
                    print(h.name)
                    print("-"*20)
                    print(h.bio)
            
            elif line.split()[0] in ("find", "search", "FIND", "SEARCH", "f"):
                args = {t.split('=')[0]: t.split('=')[1] for t in [l.replace("_", " ") for l in line.split(" ")[1:]]}
                if 'role' in args:
                    args["role"] = args["role"].split(",") # Multiple roles are comma-separated.

                for h in find_heroes(heroes, **args):
                    print(h)

            elif line.split()[0] in ("info", "INFO", "i", "about"):
                h = find_first_hero(heroes, " ".join(line.split()[1:]))
                if h is None:
                    print("Hero " + " ".join(line.split()[1:]) + " not found.")
                    continue
                else:
                    print(h.info())
            
    except EOFError as e:
        pass
    except KeyboardInterrupt as e:
        pass

    finally:
        print("") # Newline for formatting.
