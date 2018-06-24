#include <PubSubClient.h>
#include <ESP8266WiFi.h>
#include <Bounce2.h>

// Use these lines to setup MQTT Server and WiFi
#define MQTT_SERVER "<<redacted>>"
const char *ssid = "<<redacted>>";
const char *password = "<<redacted>>";

// Define GPIO on ESP8266
const int buttonPin = D1;
const int relayPin = D4;

// Topics to Publish or Subscribe to
char *doorbellbuttonTopic = "home/doorbell/doorbell";
char *doorbellsoundTopic = "home/doorbell/sound";

// Create an instance of the bounce class
Bounce doorbellbutton = Bounce();

// Define when relay is on or off
#define RELAY_ON 0
#define RELAY_OFF 1

// Define variables
unsigned int doorbellDelay = 5000; // Interval (milliseconds) at which to keep doorbell sensor triggered to prevent multiple ringings
unsigned int ringTime = 700;       // How long the relay is on (milliseconds)
boolean doorbellSound = 1;         // Used to keep track if the doorbell should sound or be silent.  Value recieved from doorbell on/off switch (0=off, 1=on)
int buttonPush = 0;
int buttonState = 0;

struct bs_v
{
  boolean b = 0; // Value for button push
  boolean s = 1; // Value for sound
};

struct bs_v bsvalues;

// MQTT callback function -(Use only if topics are being subscribed to)
void callback(char *topic, byte *payload, unsigned int length)
{

  // Convert topic to string to make it easier to work with
  String topicStr = topic;
  //char byteToSend = 0;

  // Handle doorbellbuttonTopic
  if (topicStr.equals(doorbellbuttonTopic))
  {
    if (payload[0] == '1')
    {
      buttonPush = 1;
      (bsvalues) = passButtonPush(bsvalues, buttonPush);
      Serial.println(bsvalues.b);
    }
    else if (payload[0] == '0')
    {
      buttonPush = 0;
      (bsvalues) = passButtonPush(bsvalues, buttonPush);
      Serial.println(bsvalues.b);
    }
  }

  // Handle doorbellsoundTopic
  else if (topicStr.equals(doorbellsoundTopic))
  {
    if (payload[0] == '1')
    {
      doorbellSound = 1;
      (bsvalues) = passDoorbellSound(bsvalues, doorbellSound);
      Serial.println(bsvalues.s);
    }
    else if (payload[0] == '0')
    {
      doorbellSound = 0;
      (bsvalues) = passDoorbellSound(bsvalues, doorbellSound);
      Serial.println(bsvalues.s);
    }
  }
}

WiFiClient wifiClient;
PubSubClient client(MQTT_SERVER, 1883, callback, wifiClient);

void setup()
{
  // Initialize the button pin with a internal pull-up
  pinMode(buttonPin, INPUT_PULLUP);
  doorbellbutton.attach(buttonPin);
  doorbellbutton.interval(5);

  // Initialize the relay pin
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, RELAY_OFF);

  // Start the serial line for debugging
  Serial.begin(9600); // com to computer

  delay(100);

  // Start wifi subsystem
  WiFi.begin(ssid, password);

  // Attempt to connect to the WIFI network and then connect to the MQTT server
  reconnect();
  client.publish(doorbellsoundTopic, "1");

  // Wait for a bit before starting main loop
  delay(2000);
}

void loop()
{
  // Reconnect if connection is lost
  if (!client.connected() && WiFi.status() == 3)
  {
    reconnect();
  }

  // Maintain MQTT connection
  client.loop();

  // Monitor the button
  checkButton();

  // Handle doorbellbutton
  if (bsvalues.b == 1 && bsvalues.s == 1)
  {
    digitalWrite(relayPin, RELAY_ON);
    delay(ringTime);
    bsvalues.b = 0;
    digitalWrite(relayPin, RELAY_OFF);
    delay(doorbellDelay);

    doorbellbutton.update();
    buttonState = doorbellbutton.read();
    //Serial.println("Will ring");
  }
  else if (bsvalues.b == 0)
  {
    digitalWrite(relayPin, RELAY_OFF);
  }
  else
  {
    digitalWrite(relayPin, RELAY_OFF);
  }

  // Delay to allow ESP8266 WIFI functions to run
  delay(10);
}


struct bs_v passButtonPush(struct bs_v, int buttonPush)
{
  //struct bs_v bsvalues;
  bsvalues.b = buttonPush;
  return bsvalues;
}

struct bs_v passDoorbellSound(struct bs_v, int doorbellSound)
{
  //struct bs_v bsvalues;
  bsvalues.s = doorbellSound;
  return bsvalues;
}

void checkButton()
{

  buttonState = digitalRead(buttonPin);
    Serial.println(buttonState);
  doorbellbutton.update();
  buttonState = doorbellbutton.read();

  if (doorbellbutton.fell() == 1)
  {
    Serial.println("fell");
    client.publish(doorbellbuttonTopic, "1");
  }
  else if (doorbellbutton.rose() == 1)
  {
    Serial.println("rose");

    client.publish(doorbellbuttonTopic, "0");
  }
  else
  {
    //client.publish(doorbellbuttonTopic, "0");
    //buttonPush = 1;
  }
}

void failMQTTcheckButton()
{

  buttonState = digitalRead(buttonPin);
  //buttonState = doorbellbutton.read();
  doorbellSound = 1;

  if (buttonState == HIGH)
  {
    buttonPush = 1;
  }

  // Else if relay is on and button is pushed publish Off state to doorbellbuttonTopic
  else if (buttonState == LOW)
  {
    buttonPush = 0;
  }
}

void reconnect()
{
  //attempt to connect to the wifi if connection is lost
  if (WiFi.status() != WL_CONNECTED)
  {
    //debug printing
    Serial.print("Connecting to ");
    Serial.println(ssid);

    //loop while we wait for connection
    while (WiFi.status() != WL_CONNECTED)
    {
      delay(500);
      Serial.print(".");
    }

    //print out some more debug once connected
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
  }

  //make sure we are connected to WIFI before attemping to reconnect to MQTT
  if (WiFi.status() == WL_CONNECTED)
  {
    // Loop until we're reconnected to the MQTT server
    while (!client.connected())
    {
      Serial.print("Attempting MQTT connection...");

      failMQTTcheckButton();

      // Generate client name based on MAC address and last 8 bits of microsecond counter
      String clientName;
      clientName += "esp8266-";
      uint8_t mac[6];
      WiFi.macAddress(mac);
      clientName += macToStr(mac);

      //if connected, subscribe to the topic(s) we want to be notified about
      if (client.connect("(char*) clientName.c_str()", "<<redacted>>", "<<redacted>>"))
      {
        Serial.print("\tMQTT Connected");
        client.subscribe(doorbellbuttonTopic);
        client.subscribe(doorbellsoundTopic);
      }

      //otherwise print failed for debugging
      else
      {
        Serial.println("\tFailed.");
        abort();
      }
    }
  }
}

// Generate unique name from MAC addr
String macToStr(const uint8_t *mac)
{

  String result;

  for (int i = 0; i < 6; ++i)
  {
    result += String(mac[i], 16);

    if (i < 5)
    {
      result += ':';
    }
  }

  return result;
}