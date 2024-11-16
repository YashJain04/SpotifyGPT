import streamlit as sl # streamlit for user interface

from dotenv import load_dotenv # load environment variables
import os # load environment variables
load_dotenv() # load .env file

import openai # openai library
from openai import OpenAI
client = OpenAI() # set up the client (OPENAI_API_KEY environment variable)

import spotipy # spotify api wrapper
from spotipy import oauth2 # authorization
from spotipy.oauth2 import SpotifyOAuth # authorization
import spotipy.util as util # authorization

import json # extract/parse JSON response
import time # required for spinner

def authorizer():
    '''
    This function is used to authorizer the user with Spotipy/Spotify. Allows access to gain user's personal information.

    Args: N/A

    Return:
        spotify: The Spotify client established from the authorization token
        token: The Spotify access code for authorization
    '''
    REDIRECT_URI = "http://localhost:8502"
    SCOPE = "playlist-modify-private"

    token = util.prompt_for_user_token(
        username = "username",
        scope = SCOPE,
        client_id = os.environ["SPOTIFY_CLIENT_ID"],
        client_secret = os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri = REDIRECT_URI
    )
    
    spotify = spotipy.Spotify(auth=token)
    return (spotify, token)

def checkConfiguration(accessCode):
    '''
    IMPORTANT: This should only be user-run.
    This function checks the configuration of tokens, keys, and variables.

    Args:
        accessCode: The Spotify access token/code for authorized requests
    
    Return: N/A
    '''
    # retrieve environment variables
    spotifyClientId = os.environ["SPOTIFY_CLIENT_ID"]
    spotifyClientSecret = os.environ["SPOTIFY_CLIENT_SECRET"]

    # print and check configuration
    print(f"Your Spotify Access Code is: {accessCode}")
    print(f"Your OpenAI API Key is: {client.api_key}")
    print(f"Your Spotify Client ID is: {spotifyClientId}")
    print(f"Your Spotify Client Secret is: {spotifyClientSecret}")

def configureStreamlit():
    '''
    This functions sets up the front-end using Streamlit.

    Args: N/A

    Return:
        prompt: The users choice of music
        numberOfSongs: The amount of songs generated
    '''
    # set up the title and headers
    sl.title("_Spotify:violet[GPT]_")
    sl.header("What type of music are you feeling today?")

    # create form for user
    with sl.form("Music Playlist"):
        # inputs from the user
        prompt = sl.text_area("Enter your music vibe here...")
        numberOfSongs = sl.slider("Number of Songs:", 1, 20, 5)
        sl.form_submit_button("Create Playlist!")

        # return inputs
        return (prompt, numberOfSongs)

def chatGPT(gptModel, prompt, numberOfSongs):
    '''
    This function uses ChatGPT to generate songs based off users input.

    Args:
        gptModel: The GPT model version in use
        prompt: The users choice of music
        numberOfSongs: The amount of songs generated
    
    Return:
        Returns the response in a JSON format
    '''
    # set up the messages field for the AI
    messages = [
        {
            "role": "system",
            "content": "You are SpotifyGPT. The smartest music bot in the universe. You will generate songs based on a users preference that will then go into a playlist. These songs must be available on Spotify. Give each playlist a unique name and description."
        },

        {
            "role": "user",
            "content": f"Hey SpotifyGPT! Create a playlist based on my preference which is {prompt}, make sure the playlist includes {numberOfSongs} songs. Make sure the songs are available on Spotify."
        }
    ]

    # set up the functions (external functions to invoke during a conversation) field for the AI
    functions = [
        {
            "name": "createPlaylist",
            "description": "Creates a Spotify playlist from a number of songs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "playlistName": {
                        "type": "string",
                        "description": "The name of the playlist"
                    },
                    "playlistDescription": {
                        "type": "string",
                        "description": "The description of the playlist"
                    },
                    "songs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "songName": {
                                    "type": "string",
                                    "description": "The name of the song"
                                },
                                "artists": {
                                    "type": "array",
                                    "description": "The list of all the artists",
                                    "items": {
                                        "type": "string",
                                        "description": "The name of the artist"
                                    },
                                }
                            }, "required": ["songName", "artists"],
                        },
                    },
                },
                "required": ["playlistName", "playlistDescription", "songs"],
            },
        }
    ]

    # create the response
    with sl.spinner("Finding Those Songs!"):
        time.sleep(2)
        response = openai.chat.completions.create(
            model = gptModel,
            messages = messages,
            functions = functions
        )

    # output to frontend
    sl.write(response)
    
    # return output from model
    return response

def parseResponse(spotify, response):
    '''
    This function is used to parse the response from ChatGPT. Extracting the necessary arguments (playlistName, playlistDescription, allSongs, songURIS).
    
    Args:
        spotify: The client from the Spotify API Wrapper
        rseponse: The response from ChatGPT

    Return:
        playlistName: The name of the playlist
        playlistDescription: The description of the playlist
        songURIS: A unique identifier for each song
    '''
    # retrieve the arguments from the json
    arguments = json.loads(response.choices[0].message.function_call.arguments)

    # error check, return nothing if arguments are empty
    if not arguments:
        return

    # set up the variables for the playlistName, playlistDescription, allSongs
    playlistName = "SpotifyGPT - " + arguments["playlistName"]
    playlistDescription = arguments["playlistDescription"]
    allSongs = arguments["songs"] # list of all songs

    # for each song in the list of all songs, use the spotify client to search it based on it's name and artist and retrieve the URI and put it inside the list
    songURIS = [
        spotify.search(
            q=f"{song["songName"]} {','.join(song["artists"])}", limit=1
        )["tracks"]["items"][0]["uri"]
        for song in allSongs
    ]

    # return the details
    return (playlistName, playlistDescription, songURIS)

def createPlaylist(spotify, playlistName, playlistDescription, songURIS):
    '''
    This function uses the Spotipy Spotify API Wrapper to create a playlist for the user, and then add songs to it.

    Args:
        spotify: The client from the Spotify API Wrapper
        playlistName: The name of the playlist from SpotifyGPT
        playlistDescription: The description of the playlist from SpotifyGPT
        songURIS: The URI's of the song (gets the exact song)

    Return:
        playlistList: A link to the playlist (so the user can click on it and see the playlist in their account)
    '''
    # create the playlist (empty until songs are added to it)
    playlist = spotify.user_playlist_create(spotify.me()["id"], playlistName, False, description = playlistDescription)

    # add songs to empty playlist
    spotify.playlist_add_items(playlist["id"], songURIS)

    # get the playlist link to show user
    playlistLink = playlist["external_urls"]["spotify"]

    # return playlist
    return playlistLink

def main():
    '''
    This function runs the program
    '''
    # authorize and authenticate user
    spotify, accessCode = authorizer()

    # if not authorized don't continue
    if not accessCode:
        return

    # checkConfiguration(accessCode) # IMPORTANT: uncomment this if you want to verify configuration

    # configure streamlit to set up the frontend
    prompt, numberOfSongs = configureStreamlit()

    if prompt != "":
        # create a response
        response = chatGPT("gpt-4o", prompt, numberOfSongs)
        
        with sl.spinner("Creating Playlist!"):
            time.sleep(2)
            # parse the response
            playlistName, playlistDescription, songURIS = parseResponse(spotify, response)

            # create a playlist with details
            playlistLink = createPlaylist(spotify, playlistName, playlistDescription, songURIS)

        # link the playlist
        sl.write (
            f"Playlist Created. <a href = '{playlistLink}'>Click Here!</a>",
            unsafe_allow_html=True
        )

# run the main function
main()