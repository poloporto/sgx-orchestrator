#!/usr/bin/env python3
import argparse
import traceback

import atexit
from kubernetes import config
from kubernetes.client import *
from kubernetes.client.rest import ApiException

config.load_kube_config()
api = CoreV1Api()

scheduler_name = "binpack"
pods = []


def launch_sgx_pod(pod_name: str, duration: int, requested_pages: int, actual_pages: int):
    global pods
    print("Launching a Pod that lasts %d seconds, requests %d pages and allocates %d pages" % (
        duration, requested_pages, actual_pages
    ))

    pod = V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=V1ObjectMeta(
            name="experiment-%s" % pod_name
        ),
        spec=V1PodSpec(
            termination_grace_period_seconds=0,
            scheduler_name=scheduler_name,
            containers=[V1Container(
                name="sgx-app",
                image="172.28.3.1:5000/sgx-app:1.1",
                args=["-d", str(duration), str(actual_pages)],
                resources=V1ResourceRequirements(
                    limits={
                        "intel.com/sgx": requested_pages
                    },
                    requests={
                        "intel.com/sgx": requested_pages
                    }
                )
            )],
            restart_policy="OnFailure"
        )
    )

    try:
        api.create_namespaced_pod("default", pod)
        pods.append(pod)
    except ApiException:
        print("Creating Pod failed!")
        traceback.print_exc()


@atexit.register
def cleanup_pods():
    for p in pods:
        pod_name = p.metadata.name
        print("Deleting %s" % pod_name)
        try:
            api.delete_namespaced_pod(pod_name, "default", V1DeleteOptions())
        except ApiException:
            print("Delete failed")


def main():
    launch_sgx_pod("test", 30, 5000, 6000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiments runner")
    parser.add_argument("-s", "--scheduler", type=str, default=scheduler_name, nargs="?",
                        help="Name of the custom scheduler to use")
    args = parser.parse_args()
    scheduler_name = args.scheduler

    main()