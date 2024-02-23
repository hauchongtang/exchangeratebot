import heapq
import matplotlib.pyplot as plt
import io

from common import EMPTY_LIST_PROVIDED_ERROR


class GraphViewer:
    def __init__(self, data: dict):
        self.peaks_indices = []
        self.data = data
        self.rates = list(data.values())
        self.dates = list(data.keys())

    def get_n_peaks(self, n: int):
        if len(self.dates) <= 0:
            return EMPTY_LIST_PROVIDED_ERROR
        heap = []
        for i in range(1, len(self.dates)-1):
            rate = self.data[self.dates[i]]
            rate_next = self.data[self.dates[i+1]]
            rate_prev = self.data[self.dates[i-1]]
            if 0 < i < len(self.dates) - 1 and rate > rate_prev and rate > rate_next:
                heapq.heappush(heap, (-rate, i))
            if len(heap) > n:
                heapq.heappop(heap)

        self.peaks_indices = [i for _, i in heap]
        return self

    def get_caption(self):
        caption = ""
        if self.rates[0] < self.rates[-1]:
            caption += f"Rates have a rising trend 💹\n"
        elif self.rates[0] == self.rates[-1]:
            caption += f"Rates have a flat trend."
        else:
            caption += f"Rates have a falling trend. 📉"
        return caption

    def generate_graph(self):
        x_list = self.dates
        y_list = self.rates

        # Add title and labels
        plt.title(f"Exchange Rate")
        plt.xlabel(f"{self.dates[0]}  -->  {self.dates[-1]}")
        plt.ylabel("Price ($)")
        plt.plot(x_list, y_list, marker='o', color='b')
        plt.plot(x_list[-1], y_list[-1], marker='*', color='r')
        plt.gca().set_xticks([])
        plt.text(self.dates[-3], self.rates[-1], f"{self.rates[-1]:.3f}")

        plot_file = io.BytesIO()
        plt.savefig(plot_file)
        plot_file.seek(0)
        return plot_file, self.get_caption()
