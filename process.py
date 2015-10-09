import sys

f = open(sys.argv[1])
url_dict = {}
url_list = []
count = 0
for line in f:
  tmp = line.strip().split()
  if tmp[0] == '[TIME]':
    url = tmp[2]
    if url == "DOMContentLoaded":
      break
    else:
      url = url[4:]
    count += 1
    if url in url_dict:
      url_dict[url] += 1
    else:
      url_dict[url] = 1
    url_list.append(url)

print "the number of objects: ", str(count)
#for item in url_dict:
#  print item, str(url_dict[item])
for url in url_list:
  print url
