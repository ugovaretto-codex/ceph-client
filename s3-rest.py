#!/usr/bin/env python3
"""Send REST request specified on the command line to S3 services.

   __author__     = "Ugo Varetto"
   __license__    = "MIT"
   __version__    = "0.2"
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
    separated key=value pairs;

    parameters and headers must *always* include key=value pairs, use "key=''"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Send REST request to S3 service')
    parser.add_argument('-b', '--bucket', dest='bucket', type=str,
                        required=False,
                        help='the S3 bucket name')
    parser.add_argument('-k', '--key', dest='key', type=str, required=False,
                        help='key name')
    parser.add_argument('-a', '--action', dest='action', type=str,
                        required=False,
                        help='action name')
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
                        required=False,
                        help='if true "payload" is interpreted as a file name',
                        nargs='?', type=bool, default=True)
    parser.add_argument('-s',
                        '--sign_payload', dest='sign_payload', required=False,
                        help='if true "payload" is interpreted as a file name',
                        nargs='?', type=bool, default=True)
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

    args = parser.parse_args()

    params = None
    if args.parameters:
        params = dict([x.split("=") for x in args.parameters.split(";")])
    headers = None
    if args.headers:
        headers = dict([x.split("=") for x in args.headers.split(";")])
    payload = args.payload
    if args.payload and args.subst_params:
        subst_dict = dict([x.split("=") for x in args.subst_params.split(";")])
        for (k, v) in subst_dict.items():
            payload = payload.replace(k, v)

    response = s3.send_s3_request(
                           config=args.config_file,
                           req_method=args.method,
                           parameters=params,
                           payload=payload,
                           sign_payload=args.sign_payload,
                           payload_is_file_name=args.payload_is_file,
                           bucket_name=args.bucket,
                           key_name=args.key,
                           action=args.action,
                           additional_headers=headers,
                           content_file=args.content_file)

    outfile = sys.stdout if response.status_code == 200 else sys.stderr
    print(f"Response status: {response.status_code}", file=outfile)
    print(f"Response headers: {response.headers}", file=outfile)

    # only print content text when not writing to file
    if response.text and not args.content_file and response.status_code == 200:
        print(f"Response body: {response.text}", file=outfile)
        print(s3.xml_to_text(response.text))
