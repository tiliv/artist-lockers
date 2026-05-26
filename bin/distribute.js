#!/usr/bin/env node

import { PinataSDK } from "pinata";
import { readFileSync } from "fs";
import { basename } from "path";

const [,, filePath, mimeType, name] = process.argv;

const pinata = new PinataSDK({
  pinataJwt: process.env.PINATA_JWT,
  pinataGateway: process.env.PINATA_GATEWAY,
});

const buffer = readFileSync(filePath);
const file = new File([buffer], name || basename(filePath), { type: mimeType });
const upload = await pinata.upload.public.file(file);

process.stdout.write(JSON.stringify(upload) + "\n");
