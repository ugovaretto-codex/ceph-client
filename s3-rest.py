#!/usr/bin/env python3
"""Send REST request specified on the command line to S3 services.

   __author__     = "Ugo Varetto"
   __license__    = "MIT"
   __version__    = "0.3"
   __maintainer__ = "Ugo Varetto"
   __email__      = "ugovaretto@gmail.com"
   __status__     = "Development"

    run with --help to see all options

    example:

        s3-rest.py --method=get --config_file=config/s3-credentials2.json \
                   --bucket=uv-bucket-3 --parameters="versions=''

        will print all the version information associated to a bucket

        s3-rest.py --method=get  --config_file=config/s3-credentials2.json

        lists all the buckets associated to a specific access+secret key

    credentials and endpoint information are read from a json file which
    must include the following information:

    {
        ...
        "access_key": "00000000000000000000000000000000",
        "secret_key": "11111111111111111111111111111111",
        "protocol"  : "http",
        "host"      : "localhost",
        "port"      : 8000
        ...
    }

    url parameters can be passed on the command line as ';' separated
    key=value pairs and will be properly urlencoded;

    additional headers can be passes as well on the command line as ';'
    separated key:value pairs;

    parameters and headers must *always* include key=value pairs, use "key="
    for missing values;

    reponse status code, headers, textual and parsed xml body is printed
    to either standard output (200 status) or standard error (non 200 status);

    supports saving content to file and substituting parameters in text
    requests before they are sent.
"""
import s3v4_rest as s3
import requests
import sys
import argparse
import time
import json
import xml.etree.ElementTree as ET 

def ok(code):
    return 200 <= code < 300


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Send REST request to S3 service')
    parser.add_argument('-b', '--bucket', dest='bucket', type=str,
                        required=False,
                        help='the S3 bucket name')
    parser.add_argument('-k', '--key', dest='key', type=str, required=False,
                        help='key name')
    parser.add_argument('-m', '--method', dest='method', type=str,
                        required=False, default='get',
                        help='method: get, put, post', action='store')
    parser.add_argument('-c', '--config_file', dest='config_file',
                        required=True,
                        help='json configuration file', type=str)
    parser.add_argument('-p', '--payload', dest='payload', required=False,
                        help='request body', type=str)
    parser.add_argument('-f',
                        '--payload_is_file', dest='payload_is_file',
                        required=False, type=bool, const=True,
                        help='if true "payload" is interpreted as a file name',
                        nargs='?', default=False)
    parser.add_argument('-s',
                        '--sign_payload', dest='sign_payload', required=False,
                        help='if true "payload" is interpreted as a file name',
                        nargs='?', type=bool, default=False, const=True)
    parser.add_argument('-t', '--parameters', dest='parameters',
                        required=False, type=str,
                        help="';' separated list of key=value pairs")
    parser.add_argument('-e', '--headers', dest='headers', required=False,
                        type=str,
                        help="';' separated list of key=value pairs")
    parser.add_argument('-n', "--save_content_to_file", dest="content_file",
                        required=False, help="save response content to file")
    parser.add_argument('-x', "--substitute_parameters", type=str,
                        dest="subst_params",
                        help="';' separated list of key=value pairs, " +
                             "substitutes key with value in request body",
                        required=False)
    parser.add_argument('-o', '--output', type=str, dest='output_type',
                        help="content output type: xml | text | binary",
                        default="xml", required=False)
    parser.add_argument('-O', '--override-configuration', type=str,
                        dest="override_config",
                        help="replaces configuration parameters, " +
                             "key=value ';' separated list",
                        required=False)
    parser.add_argument('-P', '--proxy-endpoint', type=str, dest="proxy",
                        help='send request to proxy instead, but sign ' +
                             'header using actual endpoint', required=False)
    parser.add_argument('-X', '--xml-query', type=str,
                        dest='xml_query',
                        help="search tag value in xml response",
                        required=False)
    parser.add_argument('-H', '--search-headers-keys', type=str,
                        dest='header_keys',
                        help="search header key in response header, prefix" +
                              " tags with 'aws:'",
                        required=False)
    parser.add_argument('-M', '--mute', type=bool, required=False, nargs="?",
                        help='disable logging', const=True, dest='mute')

    args = parser.parse_args()

    params = None
    if args.parameters:
        params = dict([x.split("=", 1) for x in args.parameters.split(";")])
    headers = None
    if args.headers:
        headers = dict([x.split(":", 1) for x in args.headers.split(";")])

    # if parameter substitution is required and payload is file name
    # then payload must be read from file, substitutions applied and
    # payload_is_file set to False, since substituted content needs to
    # be passed instead
    payload_is_file = args.payload_is_file
    payload = args.payload
    if args.payload and args.payload_is_file and args.subst_params:
        with open(args.payload) as f:
            payload = f.read()
            payload = payload.replace("\n", "")
            subst_dict = dict([x.split("=")
                               for x in args.subst_params.split(";")])
            for (k, v) in subst_dict.items():
                payload = payload.replace(k, v)
        payload_is_file = False

    config = None
    with open(args.config_file, 'r') as j:
        config = json.loads(j.read())

    if args.override_config:
        oc = dict([x.split("=", 2) for x in args.override_config.split(";")])
        config.update(oc)

    start = time.perf_counter()
    response = s3.send_s3_request(
                           config=config,
                           req_method=args.method,
                           parameters=params,
                           payload=payload,
                           sign_payload=args.sign_payload,
                           payload_is_file_name=payload_is_file,
                           bucket_name=args.bucket,
                           key_name=args.key,
                           additional_headers=headers,
                           content_file=args.content_file,
                           proxy_endpoint=args.proxy)
    end = time.perf_counter()
    if not args.mute:
        print("Elapsed time: " + str(end - start) + " (s)")
        outfile = sys.stdout if ok(response.status_code) else sys.stderr
        print(f"Response status: {response.status_code}", file=outfile)
        print(f"Response headers: {response.headers}", file=outfile)
        if response.text:
            print(f"Response body: {response.text}", file=outfile)
        # only print content text when not writing to file and when not binary
        if args.output_type.lower() == 'binary':
            sys.exit(0)

        if ok(response.status_code):
            if args.output_type.lower() == 'xml':
                print(s3.xml_to_text(response.text))
        else:
            if response.text:
                print(s3.xml_to_text(response.text))

    if args.xml_query and response.text:
        ns = {"aws": "http://s3.amazonaws.com/doc/2006-03-01/"}
        root = ET.fromstring(response.content)
        n = root.findall(args.xml_query, ns)
        for i in n:
            print(i.text)

    if args.header_keys and response.headers:
        keys = args.header_keys.split(",") if "," in args.header_keys \
                                           else args.header_keys
        if keys and type(keys) == str and keys in response.headers.keys():
            print(f"{keys}: {response.headers[keys]}")
        else:
            for k in keys:
                if k in response.headers.keys():
                    print(f"{k}: {response.headers[k]}")
