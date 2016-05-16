<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

<xsl:param name="canteenName"/>
<xsl:param name="canteenDesiredName"/>
<xsl:param name="specificDate"/>
<xsl:param name="lastFetched"/>

<xsl:template match="/">

<openmensa xmlns="http://openmensa.org/open-mensa-v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.1" xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd">



<xsl:if test="boolean(number($lastFetched)) and number($lastFetched) &gt; 1">
<xsl:comment>Last updated <xsl:value-of select="$lastFetched"/> seconds ago</xsl:comment> 
</xsl:if>


<xsl:for-each select="mensaplan/mensa">

<xsl:if test="not(boolean($canteenName)) or @ort = $canteenName">

<canteen>
    <name>
        <!--<xsl:value-of select="@ort"/>-->
        <xsl:value-of select="$canteenDesiredName"/>
    </name>
    <xsl:for-each select="tagesplan">
        <xsl:variable name="closed" select="text"/>
        <xsl:variable name="germandate" select="@datum"/>
        <xsl:variable name="normaldate">
            <xsl:value-of select=" 
               concat(
               substring-after(substring-after($germandate,'.'),'.') , '-',
               format-number( substring-before(substring-after($germandate,'.'),'.'), '00') , '-',
               format-number( number( substring-before($germandate,'.')), '00') 
               )
              " />
        </xsl:variable>
        
        <xsl:if test="not(boolean($specificDate)) or $specificDate = $normaldate">
  
        <day date="{$normaldate}">
            <xsl:if test="string-length($closed) &gt; 0">
                <closed/>
            </xsl:if>
            <xsl:for-each select="linie">
                <category name="{@ausgabe}">
                    <xsl:for-each select="gericht">
                        <meal>
                            <name>
                                <xsl:value-of select="text"/>
                            </name>
                            <note>
                                <xsl:value-of select="text_en"/>
                            </note>
                            <xsl:if test="studi &gt; 0.0">
                                <price role="student">
                                    <xsl:value-of select="studi"/>
                                </price>
                            </xsl:if>
                            <xsl:if test="bed &gt; 0.0">
                                <price role="employee">
                                    <xsl:value-of select="bed"/>
                                </price>
                            </xsl:if>
                            <xsl:if test="gast &gt; 0.0">
                                <price role="other">
                                    <xsl:value-of select="gast"/>
                                </price>
                            </xsl:if>
                        </meal>
                    </xsl:for-each>
                </category>
            </xsl:for-each>
        </day>
		
		</xsl:if> 
    </xsl:for-each>
</canteen>
</xsl:if>
</xsl:for-each>
</openmensa>
</xsl:template>
</xsl:stylesheet>
