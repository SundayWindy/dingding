REGISTRY ?= dcr.ruicore.io
IMAGE_NAME ?= ruicore/tp-dingding-be
IMAGE_TAG ?= v1.0.0
PIP_INDEX_URL ?= https://mirrors.aliyun.com/pypi/simple/

install:
	pip3 install --require-virtualenv -U -i ${PIP_INDEX_URL} pip wheel
	pip3 install --require-virtualenv -U -i ${PIP_INDEX_URL} -r requirements.txt

run:
	uvicorn tpdingding.app:app --reload

docker-build:
	docker build --build-arg PIP_INDEX_URL=${PIP_INDEX_URL} -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .

docker-push:
	docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

docker-build-push: docker-build docker-push

docker-buildx-push: docker-buildx docker-push

docker-buildx:
	docker buildx build --push --platform linux/amd64 \
		--build-arg PIP_INDEX_URL=${PIP_INDEX_URL} -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .
