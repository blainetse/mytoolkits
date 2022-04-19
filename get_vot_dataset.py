import os
import requests
import zipfile
import pandas as pd

from tqdm import tqdm
from urllib.parse import urlparse, urljoin


def get_data(stack):
    """Step1: 获取数据集下载链接

    Args:
        stack: 具体要下载的数据集名称，对应到 `VOT_DATASETS` 里面的 `key` 值
    """

    VOT_DATASETS = {
        "vot2013": "http://data.votchallenge.net/vot2013/dataset/description.json",
        "vot2014": "http://data.votchallenge.net/vot2014/dataset/description.json",
        "vot2015": "http://data.votchallenge.net/vot2015/dataset/description.json",
        "vot-tir2015": "http://www.cvl.isy.liu.se/research/datasets/ltir/version1.0/ltir_v1_0_8bit.zip",
        "vot2016": "http://data.votchallenge.net/vot2016/main/description.json",
        "vot-tir2016": "http://data.votchallenge.net/vot2016/vot-tir2016.zip",
        "vot2017": "http://data.votchallenge.net/vot2017/main/description.json",
        "vot-st2018": "http://data.votchallenge.net/vot2018/main/description.json",
        "vot-lt2018": "http://data.votchallenge.net/vot2018/longterm/description.json",
        "vot-st2019": "http://data.votchallenge.net/vot2019/main/description.json",
        "vot-lt2019": "http://data.votchallenge.net/vot2019/longterm/description.json",
        "vot-rgbd2019": "http://data.votchallenge.net/vot2019/rgbd/description.json",
        "vot-rgbt2019": "http://data.votchallenge.net/vot2019/rgbtir/meta/description.json",
        "vot-st2020": "https://data.votchallenge.net/vot2020/shortterm/description.json",
        "vot-rgbt2020": "http://data.votchallenge.net/vot2020/rgbtir/meta/description.json",
        "vot-st2021": "https://data.votchallenge.net/vot2021/shortterm/description.json",
        "test": "http://data.votchallenge.net/toolkit/test.zip",
        "segmentation": "http://box.vicos.si/tracking/vot20_test_dataset.zip",
        "vot2022/rgbd": "https://data.votchallenge.net/vot2022/rgbd/description.json",
        "vot2022/depth": "https://data.votchallenge.net/vot2022/depth/description.json",
        "vot2022/stb": "https://data.votchallenge.net/vot2022/stb/description.json",
        "vot2022/sts": "https://data.votchallenge.net/vot2022/sts/description.json",
        "vot2022/lt": "https://data.votchallenge.net/vot2022/lt/description.json",
    }
    url = VOT_DATASETS[stack]
    base_url = url.rsplit("/", 1)[0] + "/"

    try:
        meta = requests.get(url).json()
    except requests.exceptions.RequestException as e:
        raise Exception("Unable to read JSON file {}".format(e))

    # global sequences_url, annos_url, fnames
    sequences_url, annos_url, fnames = [], [], []
    for sequence in meta["sequences"]:
        # get data name
        fnames.append(sequence["name"])

        # get groundtruth zip file
        url = sequence["annotations"]["url"]
        if bool(urlparse(url).netloc):
            anno_url = url
        else:
            anno_url = urljoin(base_url, url)

        # get pic zip file
        url = sequence["channels"]["color"]["url"]
        if bool(urlparse(url).netloc):
            frame_url = url
        else:
            sequence_url = urljoin(base_url, url)

        annos_url.append(anno_url)
        sequences_url.append(sequence_url)

    return sequences_url, annos_url, fnames


def write2csv(csvfile, fnames, urls):
    """Step2: 将下载链接保存到 csv 文件中

    Args:
        csvfile: str 将下载链接等信息保存到 `csv` 文件，对应文件名 `{version}_sequences.csv` 以及 `{version}_anno.csv`
        fnames: [list: str] 对应着每一个 `sequence` 的名称，也可以理解为 `sequences`
        urls: [list: str] 对应着每一个 `sequence/frame` 的下载链接
    """

    # 1.创建一个 DataFrame 作为一行写入，以键值对——字典的形式存储
    df = pd.DataFrame({"filename": fnames, "urls": urls, "state": [False] * 50})
    # 2.将 DataFrame 存储为 csv 文件，index 表示是否显示行名称（可以是数字，也可以是自定义的字符串）default=True
    df.to_csv(csvfile, index=0)


def run_writer(fnames, sequences_url, annos_url):
    """执行 `write2csv`，将数据集信息写入到文件中"""
    if not os.path.exists(csvfile["sequences"]):
        write2csv(csvfile["sequences"], fnames, sequences_url)
    if not os.path.isfile(csvfile["annos"]):
        write2csv(csvfile["annos"], fnames, annos_url)


def download(url, folder_path, fname, use_proxy=False):
    """Step3: 下载数据

    Args:
        url: 下载链接
        folder_path: 下载的数据集文件保存路径
        fname: 每一个 `sequence` 对应的名字
        use_proxy: 是否使用代理
    """

    # 屏蔽warning信息
    requests.packages.urllib3.disable_warnings()
    # 构建自己的代理 IP 池
    proxies = {
        # 这里修改为自己的代理端口号，可在代理软件中进行查看更改，clash 默认是7890
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    }

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)  # 创建存放每一个图片集的单独文件夹

    fname = os.path.join(folder_path, f"{fname}.zip")

    ############# 断点续传实现 ##################
    # 第一次请求是为了得到文件总大小
    response = requests.get(
        url, stream=True, verify=False, proxies=proxies if use_proxy else ""
    )
    total_size = int(response.headers["Content-Length"])

    if os.path.isfile(fname):
        temp_size = os.path.getsize(fname)  # 本地已经下载的文件大小
        if temp_size == total_size:
            print(
                # 注意双引号中不能包括双引号！！！只能使用外面双引号，内部单引号
                f"{fname.split('/')[-2] + '.zip'} exists and have totaly been downloaded!"
            )
            return
    else:
        temp_size = 0

    # 显示一下下载了多少
    print(
        f"{fname.split('/')[-2] + '.zip'} downloaded: {temp_size/(1024*1024):.2f}MB || Total size: {total_size/(1024*1024):.2f}MB || Remaining download rate {1 - temp_size/total_size:.2f}"
    )
    # 核心部分，这个是请求下载时，从本地文件已经下载过的后面下载
    # headers = {'Range': 'bytes=%d-' % temp_size}
    headers = {
        "Range": f"bytes={temp_size}-{total_size}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    }
    # 重新请求网址，加入新的请求头的
    response = requests.get(
        url,
        stream=True,
        verify=False,
        headers=headers,
        proxies=proxies if use_proxy else "",
    )
    ############################################

    with tqdm.wrapattr(
        open(fname, "ab"),  # 以 ab 追加的形式写入！！！
        "write",
        miniters=1,
        desc=fname.split("/")[-2] + ".zip",
        total=int(response.headers.get("content-length", 0)),
    ) as fout:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                temp_size += len(chunk)
                fout.write(chunk)
                fout.flush()


def unzip_file(zip_src: str, dst_dir: str):
    """Step4: 解压下载的数据包

    Args:
        zip_src: 源压缩包路径
        dst_dir: 指定解压的目录

    Returns: bool
        True: 表示解压成功，同时也包含该数据已经下载的信息
        False: 表示解压失败，数据集没有成功下载
    """

    try:
        with zipfile.ZipFile(file=zip_src) as zip_file:
            # Loop over each file
            # print(f"Start unzip {zip_src.split('/')[-2]}")
            for file in zip_file.namelist():
                # Extract each file to another directory
                # If you want to extract to current working directory, don't specify path
                zip_file.extract(member=file, path=dst_dir)

            print(f"{zip_src.split('/')[-2].upper()} has been unziped fully!")
            os.remove(zip_src)
            return True
    except:
        print("This is not zip file!")
        return False


def download_annos(use_proxy=True):
    """Step5: 下载每一个 `sequence` 对应的 `annotation` 或者说 `groundtruth.txt`

    Args:
        use_proxy: 是否使用代理
    """

    annos = pd.read_csv(csvfile["annos"], header=0, index_col=0, usecols=[0, 1, 2])
    for fname, (url, state) in annos.iterrows():
        folder_path = os.path.join(os.getcwd(), root, fname)

        # 判断是否已经下载完成
        if state:
            print(
                f"{fname} exists and have totaly been downloaded and unziped! Going to download and unzip the next."
            )
        else:
            ## download
            download(url, folder_path, "groundtruth", use_proxy)
            ## unzip
            zip_src = folder_path + "/groundtruth.zip"
            dest_dir = os.path.join(os.getcwd(), root, fname)
            state = unzip_file(zip_src, dest_dir)
            ## 将新的状态添加进入文件中
            annos.loc[fname, "state"] = state
            # print(annos.loc[fname][1])
            annos.to_csv(csvfile["annos"], index=fnames, encoding="utf-8")


def download_sequences(use_proxy=True):
    """Step5: 下载 `video sequences`

    Args:
        use_proxy: 是否使用代理
    """

    sequences = pd.read_csv(
        csvfile["sequences"], header=0, index_col=0, usecols=[0, 1, 2]
    )
    for fname, (url, state) in sequences.iterrows():
        folder_path = os.path.join(os.getcwd(), root, fname)

        # 判断是否已经下载完成
        if state:
            print(
                f"{fname} exists and have totaly been downloaded and unziped! Going to download and unzip the next."
            )
        else:
            ## download
            download(url, folder_path, "color", use_proxy)
            ## unzip
            zip_src = folder_path + "/color.zip"
            dest_dir = os.path.join(os.getcwd(), root, fname, "color")
            state = unzip_file(zip_src, dest_dir)
            sequences.loc[fname, "state"] = state
            sequences.to_csv(csvfile["annos"], index=fnames, encoding="utf-8")


def write2list(root, fnames):
    """Step5: 下载 `list`，存放在当前数据据目录下，后期读取数据集的时候会用到"""

    if not os.path.exists(root):
        os.makedirs(root)
    flist = os.path.join(root, "list.txt")

    with open(flist, "w") as fl:
        fl.writelines([fname + "\n" for fname in fnames])


def write2squence(root, sequence):
    """Step5: 下载 `sequence`，存放在每一个 `sequence` 目录下，保存当前序列的相关信息"""
    for fname in fnames:
        ## 添加 sequence 文件
        fsequence = os.path.join(root, fname, "sequence")
        # print(fsequence)
        if not os.path.exists(fsequence):
            fsequence = open(fsequence, encoding="utf-8", mode="w")
            fsequence.writelines(sequence)
            fsequence.writelines(f"name={fname}\r\n")
            fsequence.flush()
            fsequence.close()


if __name__ == "__main__":
    ## 0.初始化相关数据
    # stack = "vot2022/lt"
    # version = "VOT2022_LT"
    stack = input("请输入要下载的数据集名称：")  # 注意：这里的名称要和 `VOT_DATASETS` 里面的 `key` 对应
    version = input("请输入要保存的数据集名称：")  # 这里随便起一个名字，易懂即可，比如 `votlt2022`

    root = f"./{version}"
    sequence = ["channels.color=color/%08d.jpg\r\n", "format=default\r\n", "fps=30\r\n"]
    csvfile = {
        "sequences": version + "_sequences.csv",
        "annos": version + "_annos.csv",
    }

    ## 1.获取下载链接
    sequences_url, annos_url, fnames = get_data(stack)
    # 输出下载链接
    # for fname, url in zip(fnames, sequences_url):
    #     print(f"{fname}: {url}")

    ## 2.将下载链接保存到 csv 文件
    run_writer(fnames, sequences_url, annos_url)

    ## 3.下载数据
    # download_annos(use_proxy=True)  # 3.1 下载 groundtruth.txt
    print("Done, groundtruth.txt has been downloaded!")

    download_sequences(use_proxy=True)  # 3.2 下载 sequences
    print("Done, color.zip has been downloaded!")

    write2list(root, fnames)  # 3.3 下载 list
    print("Done, list has been downloaded!")

    write2squence(root, sequence)  # 3.4 下载 sequence
    print("Done, sequence has been downloaded!")
