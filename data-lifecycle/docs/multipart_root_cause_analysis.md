# Multipart Upload Root Cause Analysis

## Goal

Understand why large uploads to AWS/S3 fail in the `aws-cli` and `smart_open` code paths while succeeding via `rclone`, using the minimal Docker repro environment in this repository.

## Outcome

Operational outcome from this investigation:

1. Large single-request upload shapes were unstable across client families in the repro harness.
2. Multipart uploads with smaller request bodies were materially more reliable.
3. Stage 4 remained on the `smart_open` multipart path, but production writes into the multipart writer were reduced to `1 MiB` chunks.

## Repro Environment

- Host source file: `/tmp/HET3-6.raw.h5`
- File size: `2250362144` bytes (`~2.1 GiB`)
- Default AWS test destination: `s3://braingeneers-backups-dev/stage4-debug/`
- Repro entrypoint: `make data-lifecycle-stage4-upload-repro`
- Container image: `braingeneers/data-lifecycle:latest`

## Observed Versions

Host environment:

- `aws-cli/1.22.34`
- `Python 3.11.3`
- `OpenSSL 1.1.1t`
- `boto3 1.35.95`
- `botocore 1.35.99`
- `urllib3 1.26.16`

Container observations:

- `Python 3.10.10`
- `OpenSSL 3.1.0`
- `boto3 1.34.60`
- `botocore 1.34.60`
- `urllib3 2.0.7`
- `rclone v1.73.0`

## Bucket Region Check

- `braingeneers-backups-dev` => `us-east-1`
- `braingeneers-backups-glacier` => `us-west-2`

This matters because the repro target originally defaulted to `us-west-2` while the dev bucket is in `us-east-1`. That mismatch was corrected, but it did not resolve the upload failures.

## Experiment Log

### 1. `smart_open` multipart upload to AWS dev bucket

Command path:

- `make data-lifecycle-stage4-upload-repro`

Result:

- Failed
- Error class: `botocore.exceptions.SSLError`
- Representative message: `SSL validation failed ... EOF occurred in violation of protocol`

Conclusion:

- Baseline failure reproduced inside the Docker harness.

### 2. `smart_open` single-request upload (`multipart_upload=false`)

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_MULTIPART_UPLOAD=false DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/smart-open-singleput-us-east-1-HET3-6.raw.h5 DATA_LIFECYCLE_STAGE4_POC_AWS_REGION=us-east-1`

Result:

- Failed
- Error class: `botocore.exceptions.SSLError`
- Failure occurred on `put_object` during `close()`

Conclusion:

- The issue is not limited to multipart uploads. Single-request `PutObject` through the botocore stack also fails.

### 3. `aws s3 cp` upload to AWS dev bucket

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_UPLOADER=aws-cli DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/aws-cli-us-east-1-HET3-6.raw.h5 DATA_LIFECYCLE_STAGE4_POC_AWS_REGION=us-east-1`

Result:

- Failed
- Representative message: `Connection was closed before we received a valid response from endpoint URL ... partNumber=2`

Conclusion:

- The failure is not specific to the Python `smart_open` wrapper. The AWS CLI stack also fails on the same file in the same container.

### 4. `rclone copyto` upload to AWS dev bucket

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_UPLOADER=rclone DATA_LIFECYCLE_STAGE4_POC_AWS_REGION=us-east-1 DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/rclone-via-make-HET3-6.raw.h5`

Result:

- Succeeded
- Verified with `head-object`
- Final object size: `2250362144`

Conclusion:

- The network path and AWS bucket are capable of accepting this upload from the same container environment.
- The failure is therefore specific to the AWS CLI / botocore / urllib3 transfer stack, or to protocol details those clients use that `rclone` does not.

### 5. `rclone` single-request upload (`--s3-use-multipart-uploads=false`)

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_UPLOADER=rclone DATA_LIFECYCLE_STAGE4_POC_MULTIPART_UPLOAD=false DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/rclone-singlepart-default-HET3-6.raw.h5`

Result:

- Failed
- Representative message: `PutObject ... write: connection reset by peer`

Conclusion:

- `rclone` is not immune in general.
- It only succeeds once multipart uploads are enabled.
- This is a strong indication that large single-request `PutObject` uploads are fundamentally unstable on this path.

### 6. `rclone` single-request upload with presigned requests disabled

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_UPLOADER=rclone DATA_LIFECYCLE_STAGE4_POC_MULTIPART_UPLOAD=false DATA_LIFECYCLE_STAGE4_POC_RCLONE_USE_PRESIGNED_REQUEST=false DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/rclone-singlepart-putobject-HET3-6.raw.h5`

Result:

- Failed
- Representative message: `PutObject ... write: connection reset by peer`

Conclusion:

- The failure persists when `rclone` is forced away from any presigned-request optimization.
- This reinforces the conclusion that large single-request uploads themselves are the problem, regardless of client family.

### 7. `smart_open` multipart upload with smaller `5 MiB` parts

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_PART_SIZE_MIB=5 DATA_LIFECYCLE_STAGE4_POC_COPY_CHUNK_MIB=5 DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/smart-open-5m-v2-HET3-6.raw.h5`

Result:

- Did not hit the earlier immediate `SSLError` failure mode
- Progressed past `2.0 GiB`
- The local harness eventually terminated the process with exit `137` before final object completion, so this run is incomplete rather than a confirmed success

Conclusion:

- Smaller multipart requests materially change the failure behavior for the `smart_open` / botocore stack.
- Even without a clean completion yet, this is strong evidence that per-request body size is a major part of the root cause.

### 8. `rclone` multipart upload with large `64 MiB` chunks and concurrency `1`

Command path:

- `make data-lifecycle-stage4-upload-repro DATA_LIFECYCLE_STAGE4_POC_UPLOADER=rclone DATA_LIFECYCLE_STAGE4_POC_RCLONE_CHUNK_SIZE_MIB=64 DATA_LIFECYCLE_STAGE4_POC_RCLONE_UPLOAD_CONCURRENCY=1 DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL=s3://braingeneers-backups-dev/stage4-debug/rclone-multipart-64m-1x-HET3-6.raw.h5`

Result:

- Did not complete within the observation window
- No finished object was visible via `head-object` during that window

Conclusion:

- This run was inconclusive, but it behaved substantially worse than `rclone`'s default multipart path.
- It is consistent with the idea that larger multipart request bodies are more fragile.

### 9. AWS CLI debug trace

Command path:

- Dockerized `aws s3 cp --debug` against the same dev bucket and file, with the log written to `/tmp/aws_cli_debug_stage4.log`

Observed details:

- The AWS CLI uses multipart upload for this file
- It eagerly schedules many `UploadPartTask` operations almost immediately
- The initial multipart setup request is a zero-length `POST ... ?uploads`
- The debug trace confirms the botocore / s3transfer stack is driving many concurrent `UploadPart` requests

Conclusion:

- The AWS CLI failure is not a mystery higher in the stack; it is occurring in the expected botocore multipart machinery.
- Combined with the successful `rclone` multipart test and the failing single-request tests, the likely trigger is the shape and size of individual HTTPS upload requests rather than basic authentication or endpoint selection.

## Current Hypothesis

At this point, the strongest hypothesis is:

1. The failing clients (`smart_open` and `aws-cli`) share the botocore/urllib3/OpenSSL request path.
2. `rclone` succeeds only when it uses multipart uploads with relatively small request bodies.
3. Large single-request `PutObject` uploads are unstable across both client families.
4. Larger multipart request bodies also appear more fragile than smaller ones.
5. Likely candidates include:
   - per-request HTTPS body size interacting badly with the network path or remote peer
   - payload signing mode
   - trailer/checksum behavior
   - request framing / chunked transfer behavior
   - concurrency in the botocore multipart stack
   - TLS write behavior specific to the OpenSSL-based stack in this environment

## Next Experiments

Planned next:

1. Compare `rclone` default vs `rclone --s3-use-unsigned-payload=true/false`
2. Re-run `smart_open` with small parts in a longer-lived harness to confirm full completion instead of just improved progress
3. Compare `smart_open` `5 MiB`, `8 MiB`, `16 MiB`, and `32 MiB` part sizes to find a sharper threshold
4. Compare botocore multipart concurrency if we expose it directly in the POC
