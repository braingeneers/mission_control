#/bin/bash

# Increment version
VERSION=$(( $(<VERSION) + 1 ))
echo ${VERSION} > VERSION

docker build -f Dockerfile -t braingeneers/job-h5repack:latest .
docker tag braingeneers/job-h5repack:latest braingeneers/job-h5repack:v${VERSION}
docker push braingeneers/job-h5repack:latest
docker push braingeneers/job-h5repack:v${VERSION}
