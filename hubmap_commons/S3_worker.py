import logging
import time
import boto3
from botocore.exceptions import ClientError

#S3Worker is a helper class used primarily for stashing the results of large web service responses in an S3 object
#which can then be downloaded via http(s) from a client.

class S3Worker:

    #create an instance of the S3Worker, requred initialization paramerters are:
    #  theAWS_ACCESS_KEY_ID- the id of an AWS access id/key pair with access to write to a public S3 bucket
    #  theAWS_SECRET_ACCESS_KEY_KEY- the secret/key side of the AWS access id/key pair with access to write to a public S3 bucket
    #  theAWS_BUCKET_NAME- the name of the AWS S3 bucket where the results/obect will be stashed
    #  theAWS_OBJECT_URL_EXPIRATION_IN_SECS- the number of seconds that the object will be downloadable for
    def __init__(self, theAWS_ACCESS_KEY_ID, theAWS_SECRET_ACCESS_KEY, theAWS_S3_BUCKET_NAME, theAWS_OBJECT_URL_EXPIRATION_IN_SECS):

        try:
            self.aws_access_key_id = theAWS_ACCESS_KEY_ID
            self.aws_secret_access_key = theAWS_SECRET_ACCESS_KEY
            self.aws_s3_bucket_name = theAWS_S3_BUCKET_NAME
            self.aws_object_url_expiration_in_secs = theAWS_OBJECT_URL_EXPIRATION_IN_SECS
        except KeyError as ke:
            raise Exception(f"Expected configuration failed to load {ke} from constructor parameters.")

        try:
            self.s3resource = boto3.Session(
                self.aws_access_key_id,
                self.aws_secret_access_key
            ).resource('s3')
            # try an operation just to verify the Resource works so that the except clause
            # is entered here rather than another method if configuration is not correct.
            self.s3resource.meta.client.head_bucket(Bucket=self.aws_s3_bucket_name)
        except ClientError as ce:
            raise Exception(f"Unable to access S3 Resource. ce={ce} with aws_access_key_id={self.aws_access_key_id}.")


    # Write an object to the configured bucket
    # INPUTS:
    #  theText- the text that will be written to the object
    #  aUUID- A unique id to idenify the object
    # RETURNS:
    #  object_key- A unique key to identify the object (used in create_URL_for_object
    def stash_text_as_object(self, theText, aUUID):
        large_response_bucket = self.s3resource.Bucket(self.aws_s3_bucket_name)
        object_key = f"{aUUID}_{len(theText)}_{str(time.time())}"
        obj = large_response_bucket.Object(object_key)
        try:
            obj.put(Body=theText)
            return object_key
        except ClientError as ce:
            raise Exception(f"Unable to access S3 Resource. ce={ce} with app_config={app_config}.")

    # create a URL which can be used to download an object via http(s)
    # INPUTS:
    #   object_key- the object_key received from stash_text_as_object when an object was created
    # RETURNS:
    #   object_url- the created object URL as a response object from the boto S3Resource
    #               method generate_presigned_url 
    def create_URL_for_object(self, object_key):
        try:
            response = self.s3resource.meta.client.generate_presigned_url('get_object',
                                                                          Params={'Bucket': self.aws_s3_bucket_name,
                                                                                  'Key': object_key},
                                                                          ExpiresIn=self.aws_object_url_expiration_in_secs)
            return response
        except ClientError as ce:
            raise Exception(f"Unable generate URL to {self.aws_s3_bucket_name}. ce={ce}.")

