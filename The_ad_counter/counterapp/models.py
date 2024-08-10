from django.db import models


class Bundle(models.Model):
    class Meta:
        ordering = ['pk']

    phrase = models.CharField(max_length=300, blank=False, null=False)
    region = models.CharField(max_length=150, blank=False, null=False)

    def __str__(self) -> str:
        if len(self.phrase) > 25:
            return f"Bundle ({self.phrase[:25]})" + "..."
        else:
            return f"Bundle ({self.phrase})"


class Counter(models.Model):
    class Meta:
        ordering = ['pk']
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, blank=False, null=False)
    count = models.IntegerField(blank=False, null=True)
    date = models.DateTimeField(blank=False, null=False, auto_now_add=True)

    def __str__(self) -> str:
        if len(self.bundle.phrase) > 25:
            return f"Counter ({self.bundle.phrase[:25]})" + "..."
        else:
            return f"Counter ({self.bundle.phrase[:25]})"


class Ad(models.Model):
    class Meta:
        ordering = ['top']
    top = models.IntegerField(blank=False, null=False)
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, blank=False, null=False)
    link = models.CharField(max_length=300, blank=False, null=False)
