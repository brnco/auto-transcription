#!/usr/bin/env python

'''
autotranscript demos

load audio file
establish connection to Google/ Watson
send audio
receive audio
save to file
format like a transcript
diff to supplied transcript
'''
import os
import json
import base64
import argparse
import subprocess
import speech_recognition as sr
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from watson_developer_cloud.websocket import AudioSource
import util as ut


def load_audio_forSR(kwargs):
    '''
    loads audio into sr audio instance
    '''
    r = sr.Recognizer()
    with sr.AudioFile(kwargs.i) as source:
        kwargs.audio = r.record(source)
    return kwargs

def load_audio_forWatson(kwargs):
    '''
    loads audio for use with Watson
    '''
    with open(kwargs.i,'rb') as audio_file:
        audio_source = AudioSource(audio_file)
    kwargs.audio = audio_source
    return kwargs

def transcode(kwargs):
    '''
    transcodes to flac
    '''
    try:
        subprocess.check_output(['ffmpeg', '-i', kwargs.i, '-map', '0:a:0', '-ac', '2', '-ar', '16000', '-c:a', 'vorbis', '-strict', '-2', kwargs.transcodeDestination])
        kwargs.i = kwargs.transcodeDestination
    except subprocess.CalledProcessError as e:
        print(e.output)
    return kwargs

def encode_base64_audio(kwargs):
    '''
    encodes audio as base64 for Google Cloud Speech
    '''
    with open(kwargs.i, "rb") as input:
        kwargs.base64_output = base64.b64encode(input.read())
    #kwargs.base64_output = subprocess.call("base64 " + kwargs.i, shell=True)
    return kwargs

def make_request_json_forGoogle(kwargs):
    '''
    makes a request.json file for us with Google Cloud Speech
    '''
    #"uri":"gs://cloud-samples-tests/speech/brooklyn.flac"
    req = open(kwargs.google_json, "w+")
    json.dump({ "config": {
              "encoding":"OGG_OPUS",
              "sampleRateHertz": 16000,
              "languageCode": kwargs.m,
              "enableWordTimeOffsets": False
              },
              "audio": { "content":kwargs.base64_output.decode('ascii')
              }
      }, req)
    req.close()

def transcribe_google_curl_short(kwargs):
    '''
    use cURL to work with Google Cloud Speech
    for files <59.9s
    '''
    cmd = 'curl -s -H "Content-Type: application/json" '\
            '-H "Authorization: Bearer "$(gcloud auth application-default print-access-token) '\
            'https://speech.googleapis.com/v1/speech:recognize '\
            '-d @' + kwargs.google_json
    subprocess.call(cmd, shell=True)

def transcribe_google_curl_long(kwargs):
    '''
    use cURL to work with Google Cloud Speech
    for files >60s
    '''
    cmd = 'curl -X POST '\
            '-H "Authorization: Bearer "$(gcloud auth application-default print-access-token) '\
            '-H "Content-Type: application/json; charset=utf-8" '\
            '--data "' + "{'config': {'language_code': '" + kwargs.m + "','encoding':'OGG_OPUS','sampleRateHertz':16000},'audio':{'uri':'gs://auto-transcript-test/" + kwargs.i + "'}}" + '" '\
            '"https://speech.googleapis.com/v1/speech:longrunningrecognize"'
    subprocess.call(cmd, shell=True)

def get_google_transcription_result(kwargs):
    '''
    use cURL to get the results of the transcription request
    '''
    cmd = 'curl -H "Authorization: Bearer "$(gcloud auth application-default print-access-token) '\
            '-H "Content-Type: application/json; charset=utf-8" '\
            '"https://speech.googleapis.com/v1/operations/' + kwargs.n + '"'
    subprocess.call(cmd, shell=True)

def transcribe_ibm_curl(kwargs):
    '''
    use cURL protocol to work with IBM Watson
    '''
    url = "https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?profanity_filter=false&timestamps=true&model=" + kwargs.m + "_BroadbandModel"
    cmd = 'curl -X POST -u "apikey:"' + apiKey + ' '\
            '--header "Content-Type: audio/ogg" --data-binary @"' + kwargs.i + '" "' + url + '" '\
            ' >> "' + kwargs.i + '.json"'
    subprocess.call(cmd, shell=True)

def init():
    '''
    initialize variable container object
    '''
    parser = argparse.ArgumentParser(description="Generate a transcript using automated tools")
    parser.add_argument("-i", "--input", dest="i", help="the input audio file")
    parser.add_argument("-a", "--algorithm", dest="a", choices=["Google", "Watson"], help="the speech-to-text algorithm to use")
    parser.add_argument("-m", "--model", dest="m", choices=["en-US", "en-UK"], help="the speech model to use")
    parser.add_argument("-n", "--number", dest="n", default=False, help="request number for completed Google Cloud Speech call")
    args = parser.parse_args()
    kwargs = ut.dotdict({})
    kwargs.i = args.i
    kwargs.a = args.a
    kwargs.m = args.m
    kwargs.n = args.n
    kwargs.google_json = "request.json"
    '''kwargs.transcode = False
    if not kwargs.i.endswith(".ogg"):
        kwargs.transcode = True
        if kwargs.a == "Watson":
            kwargs.transcodeDestination = kwargs.i + ".ogg"'''
    return kwargs

def main():
    '''
    do the thing
    '''
    kwargs = init()
    if kwargs.n:
        get_google_transcription_result(kwargs)
    elif kwargs.a == "Watson":
        transcribe_ibm_curl(kwargs)
    elif kwargs.a == "Google":
        #kwargs = encode_base64_audio(kwargs)
        #make_request_json_forGoogle(kwargs)
        transcribe_google_curl_long(kwargs)

if __name__ == "__main__":
    main()

'''
target="${1}"
project_name=$(basename "${target}" | cut -d'.' -f1)
source_dir=$(dirname "${target}")
outdir="${source_dir}"/"${project_name}"
audio_track="${project_name}"_audio.ogg
mkdir "${outdir}"

#Extract/Convert audio track to mono FLAC at 16 kHz
ffmpeg -i "${target}" -map 0:a:0 -ac 2 -ar 16000 -c:a vorbis -strict -2 "${outdir}/${audio_track}"
cd "${outdir}"
for i in *.ogg ; do
    curl -X POST -u USERNAME:PASSWORD \
    --header "Content-Type: audio/ogg" \
    --data-binary  @"${outdir}"/"${i}" \
    "https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?profanity_filter=false&timestamps=true" >> "${outdir}"/"${project_name}".json
done

#Cleanup
rm "${outdir}"/*.ogg
cat "${outdir}"/"${project_name}".json | grep transcript | cut -d'"' -f4 > "${outdir}"/"${project_name}"_parsed.txt'''
