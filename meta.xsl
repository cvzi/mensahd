<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

<xsl:param name="name"/>
<xsl:param name="address"/>
<xsl:param name="city"/>
<xsl:param name="phone"/>
<xsl:param name="latitude"/>
<xsl:param name="longitude"/>

<xsl:param name="feed"/>
<xsl:param name="source"/>
<xsl:param name="feed_today"/>
<xsl:param name="source_today"/>
<xsl:param name="feed_full"/>
<xsl:param name="source_full"/>

<xsl:param name="times"/>
<xsl:param name="monday"/>
<xsl:param name="tuesday"/>
<xsl:param name="wednesday"/>
<xsl:param name="thursday"/>
<xsl:param name="friday"/>
<xsl:param name="saturday"/>
<xsl:param name="sunday"/>

<xsl:template match="/">

<xsl:processing-instruction name="xml-stylesheet">
  <xsl:text>type="text/css" href="https://cdn.jsdelivr.net/npm/om-style@1.0.0/basic.css"</xsl:text>
</xsl:processing-instruction>

<xsl:processing-instruction name="xml-stylesheet">
  <xsl:text>type="text/css" href="https://cdn.jsdelivr.net/npm/om-style@1.0.0/lightgreen.css"</xsl:text>
</xsl:processing-instruction>
<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd">

  <canteen>
    <name><xsl:value-of select="$name" /></name>
    <address><xsl:value-of select="$address" /></address>
    <city><xsl:value-of select="$city" /></city>
    <xsl:if test="$times">
      <phone><xsl:value-of select="$phone" /></phone>
    </xsl:if>
    <location>
        <xsl:attribute name="latitude">
          <xsl:value-of select="$latitude" />
        </xsl:attribute>
        <xsl:attribute name="longitude">
          <xsl:value-of select="$longitude" />
        </xsl:attribute>
    </location>
    <xsl:if test="$times">
      <times type="opening">
        <monday>
          <xsl:choose>
            <xsl:when test="$monday">
              <xsl:attribute name="open">
                <xsl:value-of select="$monday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </monday>
        <tuesday>
          <xsl:choose>
            <xsl:when test="$tuesday">
              <xsl:attribute name="open">
                <xsl:value-of select="$tuesday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </tuesday>
        <wednesday>
          <xsl:choose>
            <xsl:when test="$wednesday">
              <xsl:attribute name="open">
                <xsl:value-of select="$wednesday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </wednesday>
        <thursday>
          <xsl:choose>
            <xsl:when test="$thursday">
              <xsl:attribute name="open">
                <xsl:value-of select="$thursday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </thursday>
        <friday>
          <xsl:choose>
            <xsl:when test="$friday">
              <xsl:attribute name="open">
                <xsl:value-of select="$friday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </friday>
        <saturday>
          <xsl:choose>
            <xsl:when test="$saturday">
              <xsl:attribute name="open">
                <xsl:value-of select="$saturday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </saturday>
        <sunday>
          <xsl:choose>
            <xsl:when test="$sunday">
              <xsl:attribute name="open">
                <xsl:value-of select="$sunday" />
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="closed">true</xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </sunday>
      </times>
    </xsl:if>

    <xsl:if test="$feed">
      <feed name="full" priority="1">
        <schedule dayOfMonth="*" dayOfWeek="1-5" hour="8" minute="10" retry="65 1 1440" />
        <url><xsl:value-of select="$feed" /></url>
        <source><xsl:value-of select="$source" /></source>
      </feed>
    </xsl:if>

    <xsl:if test="$feed_today">
    <feed name="today" priority="0">
      <schedule dayOfMonth="*" dayOfWeek="1-5" hour="10-14" retry="5 3" />
      <url><xsl:value-of select="$feed_today" /></url>
      <source>
        <xsl:choose>
          <xsl:when test="$source_today">
            <xsl:value-of select="$source_today" />
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$source" />
          </xsl:otherwise>
        </xsl:choose>
      </source>
    </feed>
    </xsl:if>

    <xsl:if test="$feed_full">
    <feed name="full" priority="1">
      <schedule dayOfMonth="*" dayOfWeek="1-5" hour="8" minute="55" retry="60 1 1440" />
      <url><xsl:value-of select="$feed_full" /></url>
      <source>
        <xsl:choose>
          <xsl:when test="$source_full">
            <xsl:value-of select="$source_full" />
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$source" />
          </xsl:otherwise>
        </xsl:choose>
      </source>
    </feed>
    </xsl:if>

  </canteen>

</openmensa>
</xsl:template>
</xsl:stylesheet>
