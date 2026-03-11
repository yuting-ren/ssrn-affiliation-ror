import fasttext

model = fasttext.load_model('lid.176.bin')

text = 'this is the fasttext test'
prediction = model.predict(text, k=1)

print(prediction)


s = "–ü—Ä–æ–±–ª–µ–º—ã –°—Ç—Ä–∞—Ç–µ–≥–∏—á–µ—Å–∫–æ–≥–æ –¶–∏–∫–ª–∞ –≤ –°–∏—Å—Ç–µ–º–µ –ì–æ—Å—É–¥–∞—Ä—Å—Ç–≤–µ–Ω–Ω–æ–≥–æ –£–ø—Ä–∞–≤–ª–µ–Ω–∏—è:  –û–ø—Ç–∏–º–∏–∑–∞—Ü–∏—è –ú–µ—Ö–∞–Ω–∏–∑–º–æ–≤ –í—ã—Ä–∞–±–æ—Ç–∫–∏ –∏ –†–µ–∞–ª–∏–∑–∞—Ü–∏–∏ –†–µ—à–µ–Ω–∏–π"  # should be "élève"
# fixed = s.encode("latin1").decode("utf-8")
# print(fixed)







print(ftfy.fix_text(s))
