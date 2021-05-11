# Copyright © 2021 Yogesh Kunjir <yogesh.kunjir@gmail.com>
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from kubernetes import config, client
import argparse

UsedSecret, UsedConfigMap, UsedPVC = [], [], []
Secrets, ConfigMap, PVC = [], [], []


def main():
    print("\nThis script is created to find unused "),
    print("resource in Kubernetes and delete them\n")
    parser = argparse.ArgumentParser(description='Parcer to get delete value')
    parser.add_argument('-d', '--delete', help='Input file name', required=False)
    args = parser.parse_args()
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
    except Exception as e:
        print("Not able to read Kubernetes cluster check Kubeconfig")
        raise RuntimeError(e)
    GetUsedResources(v1)
    DefinedSecret(v1)
    DefinedConfigMap(v1)
    DefinedPersistentVolumeClaim(v1)
    ExtraSecret = Diffrance(Secrets, UsedSecret)
    PrintList(ExtraSecret, "Secrets")
    ExtraConfigMap = Diffrance(ConfigMap, UsedConfigMap)
    PrintList(ExtraConfigMap, "ConfigMap")
    ExtraPVC = Diffrance(PVC, UsedPVC)
    PrintList(ExtraPVC, "PV Claim")
    DeleteEnabled(v1, args, ExtraSecret, ExtraConfigMap, ExtraPVC)


def DeleteEnabled(v1, args, ExtraSecret, ExtraConfigMap, ExtraPVC):
    arg = {'true', 'True', 'TRUE'}
    yes = {'yes', 'y'}
    if args.delete in arg:
        print("You have selected to delete unused items which are as above you want to continue?")
        print("Type yes or y to continue or any key to exit.")
        choice = raw_input().lower()
        if choice in yes:
            DeleteSecret(v1, ExtraSecret)
            DeleteCM(v1, ExtraConfigMap)
            DeletePVC(v1, ExtraPVC)
        else:
            print("You choose not to auto delete. Great choice! You can clean them up manually.")


def Diffrance(listA, listB):
    listC = []
    for i in listA:
        if i not in listB:
            listC.append(i)
    return listC


def PrintList(Toprint, name):
    if len(Toprint) == 0:
        print("Hurrey You don't have a unused " + name)
    else:
        print("\nExtra " + name + " are " + str(len(Toprint)) + " which are as below")
        size1 = max(len(word[0]) for word in Toprint)
        size2 = max(len(word[1]) for word in Toprint)
        borderchar = '|'
        linechar = '-'
        # print(name + " Namespaces")
        print(linechar * (size1 + size2 + 7))
        print('{bc} {:<{}} {bc}'.format(name, size1, bc=borderchar) + '{:<{}} {bc}'.format("Namespace", size2, bc=borderchar))
        print(linechar * (size1 + size2 + 7))
        for word in Toprint:
            print('{bc} {:<{}} {bc}'.format(word[0], size1, bc=borderchar) + '{:<{}} {bc}'.format(word[1], size2, bc=borderchar))
        print(linechar * (size1 + size2 + 7))
    print(" ")


def GetUsedResources(v1):
    try:
        ApiResponce = v1.list_pod_for_all_namespaces(watch=False)
    except Exception as e:
        print("Not able to reach Kubernetes cluster check Kubeconfig")
        raise RuntimeError(e)
    for i in ApiResponce.items:
        if "kube-system" in i.metadata.namespace or "kube-public" in i.metadata.namespace:
            pass
        else:
            container = i.spec.containers
            for item in container:
                if item.env is not None:
                    for secret in item.env:
                        if secret.value_from is not None:
                            if secret.value_from.secret_key_ref is not None:
                                UsedSecret.append(
                                    [secret.value_from.secret_key_ref.name, i.metadata.namespace])
                            elif secret.value_from.config_map_key_ref is not None:
                                UsedConfigMap.append(
                                    [secret.value_from.config_map_key_ref.name, i.metadata.namespace])
            for volume in i.spec.volumes:
                if volume.secret is not None:
                    UsedSecret.append([volume.secret.secret_name, i.metadata.namespace])
                elif volume.config_map is not None:
                    UsedConfigMap.append([volume.config_map.name, i.metadata.namespace])
                elif volume.persistent_volume_claim.claim_name is not None:
                    UsedPVC.append([volume.persistent_volume_claim.claim_name, i.metadata.namespace])


def DefinedSecret(v1):
    try:
        ApiResponce = v1.list_secret_for_all_namespaces(watch=False)
    except Exception as e:
        print("Not able to reach Kubernetes cluster check Kubeconfig")
        raise RuntimeError(e)
    for i in ApiResponce.items:
        if "kube-system" in i.metadata.namespace or "kube-public" in i.metadata.namespace:
            pass
        elif i.type in "kubernetes.io/tls" or i.type in "kubernetes.io/service-account-token":
            pass
        else:
            Secrets.append([i.metadata.name, i.metadata.namespace])


def DefinedConfigMap(v1):
    try:
        ApiResponce = v1.list_config_map_for_all_namespaces(watch=False)
    except Exception as e:
        print("Not able to reach Kubernetes cluster check Kubeconfig")
        raise RuntimeError(e)
    for i in ApiResponce.items:
        if "kube-system" in i.metadata.namespace or "kube-public" in i.metadata.namespace:
            pass
        else:
            ConfigMap.append([i.metadata.name, i.metadata.namespace])


def DefinedPersistentVolumeClaim(v1):
    try:
        ApiResponce = v1.list_persistent_volume_claim_for_all_namespaces(watch=False)
    except Exception as e:
        print("Not able to reach Kubernetes cluster check Kubeconfig")
        raise RuntimeError(e)
    for i in ApiResponce.items:
        PVC.append([i.metadata.name, i.metadata.namespace])


def DeleteSecret(v1, ExtraSecret):
    if len(ExtraSecret) == 0:
        print("No Unused Secret to delete. Skipping deletion.")
    else:
        for item in ExtraSecret:
            print("Deleting secret" + item[0] + "....")
            try:
                _ = v1.delete_namespaced_secret(item[0], item[1])
            except Exception as e:
                print("Not able to reach Kubernetes cluster check Kubeconfig")
                raise RuntimeError(e)
        print("Deleted All Unused Secret.")


def DeleteCM(v1, ExtraConfigMap):
    if len(ExtraConfigMap) == 0:
        print("No Unused ConfigMap to delete. Skipping deletion.")
    else:
        for item in ExtraConfigMap:
            print("Deleting ConfigMap " + item[0] + "....")
            try:
                _ = v1.delete_namespaced_config_map(item[0], item[1])
            except Exception as e:
                print("Not able to reach Kubernetes cluster check Kubeconfig")
                raise RuntimeError(e)
        print("Deleted All Unused ConfigMap.")


def DeletePVC(v1, ExtraPVC):
    if len(ExtraPVC) == 0:
        print("No Unused Persistent volume claim to delete. Skipping deletion.")
    else:
        for item in ExtraPVC:
            print("Deleting PVC " + item[0] + "....")
            try:
                _ = v1.delete_namespaced_persistent_volume_claim(item[0], item[1])
            except Exception as e:
                print("Not able to reach Kubernetes cluster check Kubeconfig")
                raise RuntimeError(e)
        print("Deleted All Unused PVC.")


if __name__ == '__main__':
    main()