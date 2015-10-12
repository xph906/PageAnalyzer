import sys
import os

#data: [{ host : { size : %d, number : %d}}]
def processPageInfo(page_url, data, threshold=5):
	host_stat = {}
	len_arr = sorted([len(item) for item in data])
	median = len_arr[len(len_arr)/2]
	min_hosts = median - 5
	max_hosts = median + 5

	qualified_data = []
	key_sets = []
	for item in data:
		if len(item) >= min_hosts and len(item) <= max_hosts:
			qualified_data.append(item)
			key_sets.append(set(item.keys()) )

	if len(qualified_data) == 0:
		print "[ERROR] no qualified browsing instance"
		return None

	common_hosts = set.intersection(*key_sets)
	if len(common_hosts) == 0:
		print "[ERROR] no common hosts"
		return None

	for host in common_hosts:
		size_arr  = sorted([item[host]['size']/1000*1000 for item in qualified_data])
		median = size_arr[len(size_arr)/2]
		if median == 0:
			median = 1000
		print "%s: [%d] %s" %(host, median, ' '.join(str(x) for x in size_arr))		


def extractDataFromFolder(path, main_host=None):
	results = []
	for root, dirs, files in os.walk(path):
		for f in files:
			if main_host and not main_host in root:
				continue

			if f != 'stdout.txt':
				continue
			fname = os.path.join(root,f)
			print fname
			obj = {}
			for line in open(fname):
				if line.startswith('[ITEM]'):
					elems = line.split()
					host = elems[1].strip()
					size = int(elems[3])
					obj[host] = {'size' : size}
			print "host size:", len(obj)
			results.append(obj)
	return results

def main():
	objs = extractDataFromFolder(sys.argv[1], sys.argv[2])
	processPageInfo("http://www.sina.com.cn",objs)

if __name__=="__main__":
	main()