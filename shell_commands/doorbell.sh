find /share/motion/front-door/*.jpg -mtime +7 -exec rm {} \;

wget -q -O /share/motion/front-door/front1.jpg http://192.168.2.21/jpg
sleep 3
wget -q -O /share/motion/front-door/front2.jpg http://192.168.2.21/jpg
sleep 3
wget -q -O /share/motion/front-door/front3.jpg http://192.168.2.21/jpg

convert -loop 0 -delay 100 /share/motion/front-door/front1.jpg /share/motion/front-door/front2.jpg /share/motion/front-door/front3.jpg /config/www/front-door/front-door-latest.gif

cp -a /config/www/front-door/front-door-latest.gif "/share/motion/front-door/front-door-$(date +"%m-%d-%y-%r").gif"