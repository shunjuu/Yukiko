import anitopy
import re
import os

from ayumi import Ayumi

def _clean_episode_name(unclean_name): 
    """
    Clean the episode name for new usage.
    Parameter unclean_name should only be the file name, no paths.
    """
    info = anitopy.parse(unclean_name)

    new_name = info['anime_title']

    if 'anime_season' in info:
        Ayumi.debug('Found anime_season "{}"'.format(info['anime_season']))
        new_name = new_name + " S" + str(info['anime_season'])

    if 'episode_number' in info:
        Ayumi.debug('Found episode_number "{}"'.format(info['episode_number']))
        new_name = new_name + " - " + str(info['episode_number'])

    if 'video_resolution' in info:
        Ayumi.debug('Found video_resolution "{}"'.format(info['video_resolution']))
        new_name = new_name + " [{}]".format(info['video_resolution'])

    if 'other' in info and 'uncensored' in info['other'].lower():
        Ayumi.debug('Detected this episode is uncensored, adding "(Uncensored)" to the title.')

    _, ext = os.path.splitext(unclean_name)
    new_name += ext

    Ayumi.debug('Complete new file name: {}'.format(new_name))
    return new_name

def _show_manually_specified(new_file):
    return re.match(r"^(.+)\/(.+)$", new_file)